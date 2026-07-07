import asyncio
import base64
import json
import re
from base64 import b64decode
import aiohttp
import cloudscraper
from bs4 import BeautifulSoup
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from logger import LOGGER

# Hardcoded keys from ApnaEx/appex_v4.py
AES_KEY = b'638udh3829162018'
AES_IV = b'fedcba9876543210'

def decrypt(enc):
    """Decrypts AES-encrypted strings from Appx API."""
    try:
        if not enc:
            return ""
        enc = b64decode(enc.split(':')[0])
        if len(enc) == 0:
            return ""
        cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
        plaintext = unpad(cipher.decrypt(enc), AES.block_size)
        return plaintext.decode('utf-8')
    except Exception as e:
        LOGGER.error(f"Decryption error: {e}")
        return ""

def decode_base64(encoded_str):
    try:
        decoded_bytes = base64.b64decode(encoded_str)
        return decoded_bytes.decode('utf-8')
    except Exception as e:
        return str(e)

async def fetch(session, url, headers):
    """Async fetch helper."""
    try:
        async with session.get(url, headers=headers) as response:
            content = await response.text()
            if response.status != 200:
                LOGGER.error(f"Error fetching {url}: {response.status} | Response: {content[:200]}")
                return {}
            
            # Some responses might be HTML wrapped JSON, handled via soup
            try:
                soup = BeautifulSoup(content, 'html.parser')
                return json.loads(str(soup))
            except json.JSONDecodeError:
                LOGGER.error(f"JSON Decode Error for {url}. Content: {content[:500]}") # Log first 500 chars
                return {}
            except Exception as e:
                # Try direct load if soup fails
                try:
                    return json.loads(content)
                except:
                    LOGGER.error(f"Failed to parse response from {url}: {e}")
                    return {}

    except Exception as e:
        LOGGER.error(f"Fetch error {url}: {e}")
        return {}

async def handle_course_topic(session, api_base, batch_id, subject_id, subject_name, topic, headers):
    """Fetch videos and PDFs for a single topic."""
    topic_id = topic.get("topicid")
    topic_name = topic.get("topic_name", "Unknown Topic")
    all_data = []

    # Get content for this topic
    content_url = f"{api_base}/get/livecourseclassbycoursesubtopconceptapiv3?courseid={topic_id}"
    resp = await fetch(session, content_url, headers)
    items = resp.get("data", [])

    for item in items:
        content_type = item.get("contentType", item.get("folder_wise_course", ""))
        name = item.get("topic_name", item.get("name", "Untitled"))

        if content_type.lower() in ("video", "VIDEO", "Video"):
            video_url = await process_video(session, api_base, item, headers)
            if video_url:
                all_data.append({
                    "url": video_url,
                    "name": name,
                    "type": "video",
                    "topicName": topic_name,
                    "subjectName": subject_name,
                    "timestamp": item.get("strtotime", item.get("createdAt", ""))
                })
        else:
            # PDF or other document
            pdf_link = item.get("file_link") or item.get("url") or item.get("link")
            if pdf_link:
                all_data.append({
                    "url": pdf_link,
                    "name": name,
                    "type": "pdf",
                    "is_pdf": True,
                    "topicName": topic_name,
                    "subjectName": subject_name,
                    "timestamp": item.get("strtotime", item.get("createdAt", ""))
                })
    return all_data

async def process_video(session, api_base, item, headers):
    """Extract and decrypt video URL from an item."""
    video_id = item.get("video_id") or item.get("_id") or item.get("id")
    if not video_id:
        return None

    # Fetch video details
    details_url = f"{api_base}/get/fetchVideoDetailsById?id={video_id}"
    resp = await fetch(session, details_url, headers)
    data = resp.get("data", {}) or resp

    enc_link = data.get("videoUrl") or data.get("url") or data.get("link")
    if not enc_link:
        return None

    # If it's a YouTube link, return as is
    if "youtube.com" in enc_link or "youtu.be" in enc_link:
        return enc_link

    # Decrypt if encrypted (ApnaEx uses AES_CBC with hardcoded key/iv)
    # The encrypted link often starts with "APPX_V="
    if "APPX_V=" in enc_link:
        enc_part = enc_link.split("APPX_V=")[-1]
        decrypted = decrypt(enc_part)
        if decrypted:
            return decrypted

    # Alternatively, try direct decryption if the link itself is encrypted (base64)
    try:
        decrypted = decrypt(enc_link)
        return decrypted
    except:
        pass

    # Fallback: return encrypted link (maybe it's not encrypted)
    return enc_link

async def extract_batch_apnaex_logic(batch_id, api_base, token, userid):
    """
    Main entry point for ApnaEx extraction logic using asyncio.
    
    Args:
        batch_id (str): The course/batch ID.
        api_base (str): Base API URL.
        token (str): Auth token (raw, without "Bearer ").
        userid (str): User ID (MANDATORY).
        
    Returns:
        list: List of dictionaries containing extracted content.
    """
    
    headers = {
        "Client-Service": "Appx",
        "source": "website",
        "Auth-Key": "appxapi",
        "Authorization": token,          # raw token, no "Bearer "
        "User-ID": str(userid),
        "User-Agent": "okhttp/4.9.1"
    }
    
    # Ensure protocol
    if not api_base.startswith("http"):
        api_base = f"https://{api_base}"

    all_data = []
    
    async with aiohttp.ClientSession() as session:
        # Fetch Subjects
        subjects_url = f"{api_base}/get/allsubjectfrmlivecourseclass?courseid={batch_id}&start=-1"
        r1 = await fetch(session, subjects_url, headers)
        
        subjects = r1.get("data", [])
        if not subjects:
            LOGGER.warning(f"No subjects found for batch {batch_id}")
            return []
            
        for subject in subjects:
            si = subject.get("subjectid")
            sn = subject.get("subject_name")
            
            # Fetch Topics for Subject
            topics_url = f"{api_base}/get/alltopicfrmlivecourseclass?courseid={batch_id}&subjectid={si}&start=-1"
            r2 = await fetch(session, topics_url, headers)
            topics = sorted(r2.get("data", []), key=lambda x: x.get("topicid"))
            
            # Process Topics sequentially (or concurrently if desired)
            for topic in topics:
                topic_results = await handle_course_topic(session, api_base, batch_id, si, sn, topic, headers)
                if topic_results:
                    all_data.extend(topic_results)
                    
    return all_data
