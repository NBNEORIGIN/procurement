import os

# Define the necessary libraries
requirements = [
    "pandas",
    "numpy",
    "matplotlib",
    "seaborn"
]

# Define the requirements file name
requirements_file = "requirements.txt"

try:
    with open(requirements_file, "w") as f:
        for lib in requirements:
            f.write(lib + "\n")
    print(f"Successfully created '{requirements_file}'.")
    print("\nTo install these requirements, run the following command in your terminal:")
    print(f"pip install -r {requirements_file}")
except IOError as e:
    print(f"Error creating '{requirements_file}': {e}")
