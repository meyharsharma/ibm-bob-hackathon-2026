from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="time-machine",
    version="0.1.0",
    author="IBM Bob Hackathon Team",
    description="A 3D visualization that renders git repositories as living cities",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/time-machine",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Version Control :: Git",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.9",
    install_requires=[
        "gitpython>=3.1.40",
        "pygit2>=1.13.3",
        "moderngl>=5.8.2",
        "moderngl-window>=2.4.4",
        "pyrr>=0.10.3",
        "numpy>=1.24.3",
        "pillow>=10.1.0",
        "flask>=3.0.0",
        "flask-cors>=4.0.0",
        "pandas>=2.1.3",
        "ibm-watson>=7.0.1",
        "ibm-cloud-sdk-core>=3.18.2",
        "requests>=2.31.0",
        "python-dotenv>=1.0.0",
        "pyyaml>=6.0.1",
        "colorlog>=6.8.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.12.0",
            "black>=23.11.0",
            "flake8>=6.1.0",
            "mypy>=1.7.1",
        ],
    },
    entry_points={
        "console_scripts": [
            "time-machine=time_machine.cli:main",
        ],
    },
)

# Made with Bob
