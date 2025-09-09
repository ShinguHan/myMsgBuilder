"""
Core Data Models for SECS-II Communication.

This module defines standardized data structures for representing
SECS-II messages and their components, ensuring type safety and
consistency throughout the application.
"""
from dataclasses import dataclass
from typing import Any, List, Union

@dataclass
class SecsItem:
    """
    Represents a single data item within a SECS-II message body.
    
    Attributes:
        type (str): The SECS-II data type identifier (e.g., 'L', 'A', 'U4').
        value (Union[List['SecsItem'], Any]): The value of the data item.
            For 'L' type, this will be a list of other SecsItem objects.
            For other types, it will be the corresponding Python type (str, int, float).
    """
    type: str
    value: Union[List['SecsItem'], Any]
