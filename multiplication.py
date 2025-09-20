"""
Multiplication Operations Module

This module provides various multiplication functions and operations.
Created for demonstrating basic Python multiplication functionality.

Author: Nikhil Nagar
"""


def multiply(a, b):
    """
    Multiply two numbers.
    
    Args:
        a (int/float): First number
        b (int/float): Second number
    
    Returns:
        int/float: Product of a and b
    """
    return a * b


def multiply_list(numbers):
    """
    Multiply all numbers in a list.
    
    Args:
        numbers (list): List of numbers to multiply
    
    Returns:
        int/float: Product of all numbers in the list
    """
    if not numbers:
        return 0
    
    result = 1
    for num in numbers:
        result *= num
    return result


def multiply_by_table(number, max_range=10):
    """
    Generate multiplication table for a given number.
    
    Args:
        number (int): Number for which to generate table
        max_range (int): Maximum range for the table (default: 10)
    
    Returns:
        dict: Dictionary with multiplier as key and product as value
    """
    table = {}
    for i in range(1, max_range + 1):
        table[i] = number * i
    return table


def print_multiplication_table(number, max_range=10):
    """
    Print multiplication table for a given number.
    
    Args:
        number (int): Number for which to print table
        max_range (int): Maximum range for the table (default: 10)
    """
    print(f"\nMultiplication Table for {number}:")
    print("-" * 30)
    for i in range(1, max_range + 1):
        result = number * i
        print(f"{number} × {i} = {result}")


def matrix_multiply(matrix1, matrix2):
    """
    Multiply two matrices (basic implementation).
    
    Args:
        matrix1 (list): First matrix (list of lists)
        matrix2 (list): Second matrix (list of lists)
    
    Returns:
        list: Resulting matrix after multiplication
    """
    # Check if multiplication is possible
    if len(matrix1[0]) != len(matrix2):
        raise ValueError("Cannot multiply matrices: incompatible dimensions")
    
    # Initialize result matrix
    rows1, cols1 = len(matrix1), len(matrix1[0])
    rows2, cols2 = len(matrix2), len(matrix2[0])
    result = [[0 for _ in range(cols2)] for _ in range(rows1)]
    
    # Perform multiplication
    for i in range(rows1):
        for j in range(cols2):
            for k in range(cols1):
                result[i][j] += matrix1[i][k] * matrix2[k][j]
    
    return result


def power_by_multiplication(base, exponent):
    """
    Calculate power using repeated multiplication.
    
    Args:
        base (int/float): Base number
        exponent (int): Exponent (must be positive)
    
    Returns:
        int/float: Result of base^exponent
    """
    if exponent < 0:
        raise ValueError("Exponent must be non-negative")
    
    if exponent == 0:
        return 1
    
    result = 1
    for _ in range(exponent):
        result *= base
    return result


def main():
    """
    Main function to demonstrate multiplication operations.
    """
    print("=== Multiplication Operations Demo ===\n")
    
    # Basic multiplication
    print("1. Basic Multiplication:")
    a, b = 15, 7
    print(f"{a} × {b} = {multiply(a, b)}\n")
    
    # List multiplication
    print("2. Multiply List of Numbers:")
    numbers = [2, 3, 4, 5]
    print(f"Numbers: {numbers}")
    print(f"Product: {multiply_list(numbers)}\n")
    
    # Multiplication table
    print("3. Multiplication Table:")
    print_multiplication_table(8, 5)
    
    # Matrix multiplication
    print("\n4. Matrix Multiplication:")
    matrix1 = [[1, 2], [3, 4]]
    matrix2 = [[5, 6], [7, 8]]
    print(f"Matrix 1: {matrix1}")
    print(f"Matrix 2: {matrix2}")
    result_matrix = matrix_multiply(matrix1, matrix2)
    print(f"Result: {result_matrix}\n")
    
    # Power by multiplication
    print("5. Power by Multiplication:")
    base, exp = 3, 4
    print(f"{base}^{exp} = {power_by_multiplication(base, exp)}\n")


if __name__ == "__main__":
    main()