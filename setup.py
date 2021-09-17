from setuptools import setup


setup(
    name="async-class",
    version="0.5.0",
    description="Write classes with async def __ainit__",
    long_description=open("README.rst").read(),
    license="MIT",
    packages=["."],
    project_urls={"Source": "https://github.com/mosquito/async-class"},
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Topic :: Internet",
        "Topic :: Software Development",
        "Topic :: Software Development :: Libraries",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "Operating System :: MacOS",
        "Operating System :: POSIX",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: Implementation :: CPython",
    ],
)
