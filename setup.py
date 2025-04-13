from setuptools import setup, find_packages

setup(
    name="harpy_agent",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "google-auth-oauthlib",
        "google-auth-httplib2",
        "google-api-python-client",
    ],
) 