import re
import struct
import sys
from dataclasses import dataclass, fields
from typing import IO, Literal, TypeVar


__all__ = ["Block"]


T = TypeVar("T", bound="Block")

# https://docs.python.org/3/library/struct.html#format-characters
_sizes: dict[int, tuple[str]] = {
    1: tuple("cbB?s" + "p"),  # `p` doesn't really belong here, but needs to be somewhere
    2: tuple("hHe"),
    4: tuple("iIlLfP"),  # P ?? --> Not clear yet if this is correct
    8: tuple("qQd"),
}

is_64bit = sys.maxsize > 2**32

_sizes[8 if is_64bit else 4] = _sizes[8 if is_64bit else 4] + tuple("nNP")

_reverse_sizes = {k: size for size, keys in _sizes.items() for k in keys}

_conversion_matrix = {
    "l": "i",  # On Mac/Ubuntu, this is 8 bytes, on Windows 4
    "L": "I",  # On Mac/Ubuntu, this is 8 bytes, on Windows 4
}


def _details(field, field_info: dict[str, object]):
    default = field.default
    had_replacements = False

    for replacement in re.findall(r"\{([^}]+)}", default):
        had_replacements = True

        if replacement not in field_info:
            raise KeyError(
                f"Unknown value '{replacement}' for field {field.name}. This replacement value should be mentioned *before* the current field."
            )
        default = default.replace(f"{{{replacement}}}", str(field_info[replacement]))

    match = re.match(rf'(\d*)([{"".join(_reverse_sizes)}])(\2*)', default)
    if not match:
        error_msg = f"Field {field.name} has an invalid (or currently unsupported) default: '{field.default}'"
        if had_replacements:
            error_msg += f" (calculated: {default})"
        error_msg += ". If this format is correct, please raise an issue on our issues page."

        raise ValueError(error_msg)

    count = match.group(1)
    type_ = match.group(2)
    repeat_ = match.group(3)

    corrected_type = _conversion_matrix.get(type_, type_)  # Convert if needed.

    assert not (
        repeat_ and count
    ), f"I can only understand either a count, or a repeat, but not '{field.default}'. Please write this as {int(count or 1)+len(repeat_)}{type_} instead."
    if repeat_:
        count = len(repeat_) + 1
    else:
        count = int(count or 1)

    return count * _reverse_sizes[corrected_type], count, corrected_type, default


def _read(block: type[T], fp: IO, alignment: Literal["@", "=", "<", ">", "!"] = "@") -> T:
    data = []
    field_info = {}
    for field in fields(block):
        byte_count, field_count, type_, default = _details(field, field_info)

        bytes_ = fp.read(byte_count)
        if len(bytes_) != byte_count:
            raise EOFError

        try:
            data_read = struct.unpack(f"{alignment}{field_count}{type_}", bytes_)
        except struct.error as ex:
            raise ValueError(
                f"An error happened while reading: {ex}. Field information: name={field.name}, format={default}, data={bytes_}"
            )

        if type_ in "sp":
            entry = data_read[0].rstrip(b"\x00")
        elif field_count == 1:
            entry = data_read[0]
        else:
            entry = list(data_read)

        field_info[field.name] = entry

        data.append(entry)

    return block(*data)


def _write(block: T, fp: IO, alignment: Literal["@", "=", "<", ">", "!"] = "@") -> None:
    field_info = {}

    for field in fields(block):
        byte_count, field_count, type_, default = _details(field, field_info)
        if field_count == 0:
            continue

        value = getattr(block, field.name)
        field_info[field.name] = value

        try:
            if type_ == "s":
                packed = struct.pack(
                    alignment + f"{field_count}{type_}", value[:field_count].ljust(field_count, b"\x00")
                )
            elif type_ in "p":
                field_count = min(field_count, 0xFF)
                packed = struct.pack(alignment + f"{field_count}p", value[:field_count])
            elif field_count == 1:
                packed = struct.pack(alignment + f"{field_count}{type_}", value)
            else:
                packed = struct.pack(alignment + f"{field_count}{type_}", *value[:field_count])
        except struct.error as ex:
            raise ValueError(
                f"An error happened while writing: {ex}. Field information: name={field.name}, format={default}, data={value}"
            )

        fp.write(packed)


@dataclass
class Block:
    @classmethod
    def read(cls, fp: IO) -> T:
        return _read(cls, fp, alignment="@")

    @classmethod
    def read_native_standard(cls, fp: IO) -> T:
        return _read(cls, fp, alignment="=")

    @classmethod
    def read_le(cls, fp: IO) -> T:
        return _read(cls, fp, alignment="<")

    @classmethod
    def read_be(cls, fp: IO) -> T:
        return _read(cls, fp, alignment=">")

    def write(self, fp: IO) -> None:
        return _write(self, fp, alignment="@")

    def write_native_standard(self, fp: IO) -> None:
        return _write(self, fp, alignment="=")

    def write_le(self, fp: IO) -> None:
        return _write(self, fp, alignment="<")

    def write_be(self, fp: IO) -> None:
        return _write(self, fp, alignment=">")

    # Aliases
    read_native = read
    read_little_endian = read_le
    read_big_endian = read_network = read_be

    write_native = write
    write_little_endian = write_le
    write_big_endian = write_network = write_be
