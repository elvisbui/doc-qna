# Modules in Python

## What is a Module?

A module is a Python file (`.py`) that contains functions, classes, and variables. Modules allow you to organize code into reusable, logical units.

## Importing Modules

```python
import math
print(math.sqrt(16))  # 4.0

from math import pi, sqrt
print(pi)       # 3.141592653589793
print(sqrt(25)) # 5.0

from math import sqrt as square_root
print(square_root(9))  # 3.0

import math as m
print(m.factorial(5))  # 120
```

## Creating Your Own Module

Any Python file can be used as a module. Create a file called `helpers.py`:

```python
# helpers.py
def add(a, b):
    return a + b

PI = 3.14159
```

Then import it from another file in the same directory:

```python
from helpers import add, PI
```

## Packages

A package is a directory containing a special `__init__.py` file and one or more modules. Packages allow hierarchical organization of modules.

```
mypackage/
    __init__.py
    module_a.py
    module_b.py
    subpackage/
        __init__.py
        module_c.py
```

Import from packages using dot notation: `from mypackage.subpackage import module_c`.

## The Standard Library

Python includes a rich standard library with modules for common tasks:

- `os` and `pathlib`: File system operations.
- `json`: JSON encoding and decoding.
- `datetime`: Date and time manipulation.
- `collections`: Specialized container types like `defaultdict` and `Counter`.
- `itertools`: Efficient looping utilities.
- `re`: Regular expressions.
