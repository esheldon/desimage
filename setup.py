import os
from setuptools import setup, find_packages

scripts = [
    'des-make-image',
    'des-make-image-fromfiles',
    'des-make-image-batch',
]
scripts = [os.path.join('bin', s) for s in scripts]

setup(
    name="desimage",
    packages=find_packages(),
    scripts=scripts,
    version="0.9.1",
    description="Make color images from DES coadds",
    license="GPL",
    author="Erin Scott Sheldon",
    author_email="erin.sheldon@gmail.com",
)
