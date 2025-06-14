import os

# Define the necessary libraries
import os
requirements = ["pandas", "numpy", "matplotlib", "seaborn", "PyQt6"] # Added PyQt6
requirements_file = "requirements.txt"
try:
    with open(requirements_file, "w") as f:
        for lib in requirements: f.write(lib + "\n")
    print(f"Successfully created/updated '{requirements_file}'.")
    print(f"To install requirements: pip install -r {requirements_file}")
except IOError as e: print(f"Error: {e}")

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
