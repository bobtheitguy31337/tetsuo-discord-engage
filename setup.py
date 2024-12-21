from setuptools import setup, find_packages

setup(
    name="tetsuo-engage",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'discord.py',
        'python-dotenv',
        'playwright',
        'python-telegram-bot',
        'nest-asyncio'
    ]
)