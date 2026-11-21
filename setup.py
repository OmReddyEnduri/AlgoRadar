#!/usr/bin/env python3
"""Setup script for AlgoRadar."""

from pathlib import Path
from setuptools import find_packages, setup

# Read the long description from README.md if it exists
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

setup(
    name="algoradar",
    version="1.0.0",
    description="High-performance terminal competitive programming contest radar and calendar workstation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="AlgoRadar Team",
    author_email="team@algoradar.dev",
    url="https://github.com/OmReddyEnduri/AlgoRadar",
    license="MIT",
    packages=find_packages(include=["algoradar", "algoradar.*"]),
    python_requires=">=3.9",
    install_requires=[
        "rich>=13.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "black>=23.0.0",
            "ruff>=0.1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "algoradar = algoradar.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Utilities",
    ],
)
