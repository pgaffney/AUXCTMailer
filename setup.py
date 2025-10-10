from setuptools import setup, find_packages

setup(
    name="auxctmailer",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pandas",
        "python-dotenv",
        "jinja2",
        "sendgrid",
        "requests",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "auxctmailer=auxctmailer.main:main",
        ],
    },
    author="Paul Gaffney",
    author_email="paul.gaffney@hey.com",
    description="Email automation system for AUXCT member communications",
    python_requires=">=3.12",
)
