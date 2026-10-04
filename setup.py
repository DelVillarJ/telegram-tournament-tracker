"""
Telegram Bot for TopDeck Tournament Tracking - Package installer.

To build the wheel or sdist:
    python -m build
    
To publish to PyPI (requires ~/.pypirc):
    twine upload dist/*
"""

from setuptools import setup, find_packages

# Read the README.md file content
with open("README.md", "r") as fh:
    long_description = fh.read()

# Get requirements from requirements.txt
requirements = []
with open("requirements.txt", "r") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#"):
            requirements.append(line)

setup(
    name="telegram-tournament-bot",
    version="1.0.0",
    author="Copilot Assistant",
    description="Telegram bot that integrates with TopDeck API to track tournaments, notify groups when they finish, and update points standings.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/telegram-tournament-bot",
    
    # Classifiers
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Communications :: Chat",
        "Topic :: Games/Entertainment",
    ],
    
    # Project URLs
    project_urls={
        "Bug Reports": "https://github.com/your-org/telegram-tournament-bot/issues",
        "Documentation": "https://github.com/your-org/telegram-tournament-bot/blob/main/docs/user-guide.md",
        "Source": "https://github.com/your-org/telegram-tournament-bot",
    },
    
    # Python requirements
    python_requires=">=3.10",
    install_requires=requirements,
    
    # Package discovery
    packages=find_packages(exclude=["tests", "docs", ".github"]),
    
    # Entry points
    entry_points={
        "console_scripts": [
            "telegram-bot=src.main:main",
        ],
    },
    
    # Additional options
    include_package_data=True,
    zip_safe=False,
)
