# Subsystem components
Step-by-step guide to deploying the oddimorf package from source.

> Note: All commands are executed through either the Windows Command Line or Linux Bash Shell.

> Note: Replace **``py``** in subsequent sections with the applicable command on the operating system, should the requisite version not be available through this command (e.g. **``python``**, **``py3.8``** or **``python3.8``**).
---

## Set up the necessary Python environment
Ensures that the requisite environment is set up.

1. Get [Python 3.8](https://www.python.org/downloads/release/python-380/) (latest version supported by Matlab as of writing) and follow the installation instructions.

2. Execute **``py --version``** to verify that the applicable version of Python is installed and in use.

3. Execute **``py -m pip install --upgrade pip``** to use the latest version of pip applicable to the Python version in use.

4. Execute **``py -m pip --version``** to verify that the pip version associated with the implemented Python installation is effected.
---

## Installing the primary Python package
Sets up the necessary base oddimorf package.

_Note: This set up process assumes that the requisite Python environment has been installed and implemented correctly._

1. Clone the repository to a working directory to which subsequent access will be retained.

2. Execute **``py -m pip install .\src``** to install the package to the system.

3. Execute **``py -m pip show oddimorf``** and confirm that the latest applicable version of the package has been effected.

4. This should be sufficient to ensure availability of the package, but the provided examples may be used to verify (see **``.\doc\guides\``**).
---
