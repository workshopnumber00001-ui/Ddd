#!/bin/bash
echo "🚀 Ensuring package directories exist..."
mkdir -p modules master constant
touch modules/__init__.py
touch master/__init__.py
touch constant/__init__.py
echo "✅ Folders and __init__.py files successfully created!"
ls -la modules
