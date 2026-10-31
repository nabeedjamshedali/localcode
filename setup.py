from setuptools import setup, find_packages

setup(
    name='localcode',
    version='1.0.0',
    description='Local AI Coding Agent — works like Claude Code, runs 100% on your machine',
    author='Nabeed',
    packages=find_packages(),
    python_requires='>=3.10',
    install_requires=[],  # Zero dependencies — only stdlib + Ollama
    entry_points={
        'console_scripts': [
            'localcode=src.main:main',
        ],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
)
