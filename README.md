# blob_reader

## Main usage:
```python
from blob_reader import Block
from dataclasses import dataclass


@dataclass
class MyObj(Block):
    _int: int = '2i'
    _txt: bytes = '10s'

    
with open('some_file.bin', 'rb') as fp:
    obj = MyObj.read(fp)
```

### API:
```python
from blob_reader import Block

Block.read     # Native reading
Block.read_be  # Big endian
Block.read_le  # Little endian

Block.write
Block.write_be
Block.write_le

# Aliases
Block.read_big_endian     = Block.read_be
Block.read_network        = Block.read_be
Block.read_little_endian  = Block.read_le

Block.write_big_endian    = Block.write_be
Block.write_network       = Block.write_be
Block.write_little_endian = Block.write_le
```

## Struct alignment
| Character | Byte order             | Size     | Alignment |
|-----------|------------------------|----------|-----------|
| `@`       | native                 | native   | native    |
| `=`       | native                 | standard | none      |
| `<`       | little-endian          | standard | none      |
| `\>`      | big-endian             | standard | none      |
| `!`       | network (= big-endian) | standard | none      |

If the first character is not one of these, `'@'` is assumed.


## Struct characters
[Official documentation](https://docs.python.org/3/library/struct.html#format-characters)

| Format | C Type             | Python type       | Standard _size | Notes    |
|--------|--------------------|-------------------|---------------|----------|
| `x`    | pad byte           | no value          |               | (7)      |
| `c`    | char               | bytes of length 1 | 1             |          |
| `b`    | signed char        | integer           | 1             | (1), (2) |
| `B`    | unsigned char      | integer           | 1             | (2)      |
| `?`    | _Bool              | bool              | 1             | (1)      |
| `h`    | short              | integer           | 2             | (2)      |
| `H`    | unsigned short     | integer           | 2             | (2)      | 
| `i`    | int                | integer           | 4             | (2)      |
| `I`    | unsigned int       | integer           | 4             | (2)      |
| `l`    | long               | integer           | 4             | (2)      |
| `L`    | unsigned long      | integer           | 4             | (2)      |
| `q`    | long long          | integer           | 8             | (2)      |
| `Q`    | unsigned long long | integer           | 8             | (2)      |
| `n`    | ssize_t            | integer           |               | (3)      |
| `N`    | size_t             | integer           |               | (3)      |
| `e`    | (6)                | float             | 2             | (4)      |
| `f`    | float              | float             | 4             | (4)      |
| `d`    | double             | float             | 8             | (4)      |
| `s`    | char[]             | bytes             |               | (9)      |
| `p`    | char[]             | bytes             |               | (8)      |
| `P`    | void*              | integer           |               | (5)      |

**Notes:**

1. The `'?'` conversion code corresponds to the _Bool type defined by C99. If this type is not available, it is simulated using a char. In standard mode, it is always represented by one byte.

1. When attempting to pack a non-integer using any of the integer conversion codes, if the non-integer has a `__index__()` method then that method is called to convert the argument to an integer before packing.

    *Changed in version 3.2*: Added use of the `__index__()` method for non-integers.

1. The `'n'` and `'N'` conversion codes are only available for the native _size (selected as the default or with the `'@'` byte order character). For the standard _size, you can use whichever of the other integer formats fits your application.

1. For the `'f'`, `'d'` and `'e'` conversion codes, the packed representation uses the IEEE 754 binary32, binary64 or binary16 format (for `'f'`, `'d'` or `'e'` respectively), regardless of the floating-point format used by the platform.

1. The `'P'` format character is only available for the native byte ordering (selected as the default or with the `'@'` byte order character). The byte order character `'='` chooses to use little- or big-endian ordering based on the host system. The struct module does not interpret this as native ordering, so the `'P'` format is not available.

1. The IEEE 754 binary16 "half precision" type was introduced in the 2008 revision of the IEEE 754 standard. It has a sign bit, a 5-bit exponent and 11-bit precision (with 10 bits explicitly stored), and can represent numbers between approximately `6.1e-05` and `6.5e+04` at full precision. This type is not widely supported by C compilers: on a typical machine, an unsigned short can be used for storage, but not for math operations. See the Wikipedia page on the half-precision floating-point format for more information.

1. When packing, `'x'` inserts one NUL byte.

1. The `'p'` format character encodes a "Pascal string", meaning a short variable-length string stored in a fixed number of bytes, given by the count. The first byte stored is the length of the string, or 255, whichever is smaller. The bytes of the string follow. If the string passed in to pack() is too long (longer than the count minus 1), only the leading `count-1` bytes of the string are stored. If the string is shorter than `count-1`, it is padded with null bytes so that exactly count bytes in all are used. Note that for unpack(), the `'p'` format character consumes `count` bytes, but that the string returned can never contain more than 255 bytes.

1. For the `'s'` format character, the count is interpreted as the length of the bytes, not a repeat count like for the other format characters; for example, `'10s'` means a single 10-byte string mapping to or from a single Python byte string, while `'10c'` means 10 separate one byte character elements (e.g., `cccccccccc`) mapping to or from ten different Python byte objects. (See Examples for a concrete demonstration of the difference.) If a count is not given, it defaults to 1. For packing, the string is truncated or padded with null bytes as appropriate to make it fit. For unpacking, the resulting bytes object always has exactly the specified number of bytes. As a special case, `'0s'` means a single, empty string (while `'0c'` means 0 characters).


## Gotchas
- `2s` saves a byte sequence of 2 bytes (ie `b'ab'`)
- `2c` saves a list of 2 times 1 byte (ie `[b'a', b'b']`)
- `2p` saves a pascal string of maximum 1 byte. As the "2" is including the 'length' byte, so `b'ab'` would be saved as `b'\x01a'` instead!


## Extensions
### Dynamic field sizes
```python
from blob_reader import Block
from dataclasses import dataclass
from io import BytesIO


@dataclass
class MyObj(Block):
    _int: int = 'H'
    _txt: bytes = '{_int}s'

stream = BytesIO(b'\x02abc')
obj = MyObj.read(stream)
# obj = MyObj(_int=2, _txt=b'ab')
```
The fieldsize should be known before the actual usage. This is enforced for both writing and reading. In writing this doesn't matter too much, but for consistency’s sake it is enforced as well. 


## Exceptions
### EOFError
This is raised when fewer bytes can be read than are actually needed.

### ValueError
If some error happened during (un)packing, more information will be given.

## KeyError
If you tried to use dynamic fields with an unknown field.

## AssertionError
When trying to match something like `2HH`. Please do write it as `3H` instead.