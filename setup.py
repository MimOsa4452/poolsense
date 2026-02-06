import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="poolsense",
    version="0.1.1",
    author="Haemish Kyd",
    author_email="haemish.kyd@gmail.com",
    description="Asynchronous Python client for getting PoolSense data.",
    long_description=long_description,
    install_requires=["aiohttp>=3.0.0"],
    license="MIT license",
    long_description_content_type="text/markdown",
    url="https://github.com/haemishkyd/poolsense",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.12',
)
