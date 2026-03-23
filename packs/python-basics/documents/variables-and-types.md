# Variables and Data Types in Python

## Variables

In Python, variables are created by assigning a value to a name using the `=` operator. Python is dynamically typed, meaning you do not need to declare the type of a variable — it is inferred from the assigned value.

```python
name = "Alice"
age = 30
height = 5.7
is_student = True
```

Variable names must start with a letter or underscore and can contain letters, digits, and underscores. Python is case-sensitive, so `count` and `Count` are different variables.

## Built-in Data Types

Python provides several built-in data types:

- **int**: Whole numbers like `42` or `-7`. Python integers have arbitrary precision.
- **float**: Decimal numbers like `3.14` or `-0.001`. Stored as 64-bit IEEE 754 doubles.
- **str**: Text strings like `"hello"` or `'world'`. Strings are immutable sequences of characters.
- **bool**: Boolean values `True` or `False`. Used in conditional expressions and logic.
- **NoneType**: The special value `None`, representing the absence of a value.

## Collections

- **list**: Ordered, mutable sequence. Created with `[1, 2, 3]`.
- **tuple**: Ordered, immutable sequence. Created with `(1, 2, 3)`.
- **dict**: Key-value mapping. Created with `{"key": "value"}`.
- **set**: Unordered collection of unique elements. Created with `{1, 2, 3}`.

## Type Conversion

Use built-in functions to convert between types:

```python
int("42")       # string to int -> 42
float("3.14")   # string to float -> 3.14
str(100)        # int to string -> "100"
list((1, 2, 3)) # tuple to list -> [1, 2, 3]
```
