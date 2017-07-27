import os
from distutils.core import setup

scripts=['des-make-image']
scripts=[os.path.join('bin',s) for s in scripts]

setup(
    name="desimage", 
    packages=['desimage'],
    scripts=scripts,
    version="0.9.0",
    description="Make color images from DES coadds",
    license = "GPL",
    author="Erin Scott Sheldon",
    author_email="erin.sheldon@gmail.com",
)




