# Functions in Python

## Defining Functions

Functions are defined using the `def` keyword followed by the function name, parameters in parentheses, and a colon. The function body is indented.

```python
def greet(name):
    return f"Hello, {name}!"
```

## Parameters and Arguments

Python supports several types of parameters:

- **Positional parameters**: Matched by position in the call.
- **Default parameters**: Have a default value if not provided.
- **Keyword arguments**: Specified by name in the call.
- **\*args**: Collects extra positional arguments into a tuple.
- **\*\*kwargs**: Collects extra keyword arguments into a dictionary.

```python
def create_profile(name, age=25, *hobbies, **metadata):
    return {
        "name": name,
        "age": age,
        "hobbies": hobbies,
        "metadata": metadata,
    }
```

## Return Values

Functions return values using the `return` statement. A function without a `return` statement implicitly returns `None`. Functions can return multiple values as a tuple.

```python
def divide(a, b):
    quotient = a // b
    remainder = a % b
    return quotient, remainder

q, r = divide(17, 5)  # q=3, r=2
```

## Lambda Functions

Lambda functions are small anonymous functions defined with the `lambda` keyword. They are limited to a single expression.

```python
square = lambda x: x ** 2
numbers = [1, 2, 3, 4]
squared = list(map(square, numbers))  # [1, 4, 9, 16]
```

## Scope

Variables defined inside a function are local to that function. Use the `global` keyword to modify a global variable from within a function, or `nonlocal` to modify a variable from an enclosing scope.
