from dataclasses import dataclass, fields
from io import BytesIO

from pytest import approx, fixture, raises

from blob_reader import Block


@dataclass
class FullCapabilities(Block):
    char_array: list[bytes] = "2c"
    char_single: bytes = "c"
    signed_char_array: list[int] = "2b"
    signed_char_single: int = "b"
    unsigned_char_array: list[int] = "2B"
    unsigned_char_single: int = "B"
    _bool_array: list[bool] = "2?"
    _bool_single: bool = "?"
    short_array: list[int] = "2h"
    short_single: int = "h"
    unsigned_short_array: list[int] = "2H"
    unsigned_short_single: int = "H"
    _int_array: list[int] = "2i"
    _int_single: int = "i"
    unsigned_int_array: list[int] = "2I"
    unsigned_int_single: int = "I"
    long_array: list[int] = "2l"
    long_single: int = "l"
    unsigned_long_array: list[int] = "2L"
    unsigned_long_single: int = "L"
    long_long_array: list[int] = "2q"
    long_long_single: int = "q"
    unsigned_long_long_array: list[int] = "2Q"
    unsigned_long_long_single: int = "Q"
    ssize_t_array: list[int] = "2n"
    ssize_t_single: int = "n"
    size_t_array: list[int] = "2N"
    size_t_single: int = "N"
    # (6): list[int] = "2e"
    # (6): int = "e"
    float_array: list[float] = "2f"
    float_single: float = "f"
    double_array: list[float] = "2d"
    double_single: float = "d"
    string: bytes = "6s"
    pascal_string: bytes = "6p"
    void_pointer_array: list[int] = "2P"
    void_pointer_single: int = "P"


@fixture
def data() -> FullCapabilities:
    return FullCapabilities(
        char_array=[b"a", b"b"],
        char_single=b"c",
        signed_char_array=[-1, -2],
        signed_char_single=-3,
        unsigned_char_array=[2**7 + 1, 2**7 + 2],
        unsigned_char_single=2**7 + 3,
        _bool_array=[True, False],
        _bool_single=True,
        short_array=[-1, -2],
        short_single=-3,
        unsigned_short_array=[2**15 + 1, 2**15 + 2],
        unsigned_short_single=2**15 + 3,
        _int_array=[-1, -2],
        _int_single=-3,
        unsigned_int_array=[2**31 + 1, 2**31 + 2],
        unsigned_int_single=2**31 + 3,
        long_array=[-1, -2],
        long_single=-3,
        unsigned_long_array=[2**31 + 1, 2**31 + 2],
        unsigned_long_single=2**31 + 3,
        long_long_array=[-1, -2],
        long_long_single=-3,
        unsigned_long_long_array=[2**63 + 1, 2**63 + 2],
        unsigned_long_long_single=2**63 + 3,
        ssize_t_array=[123, 456],
        ssize_t_single=789,
        size_t_array=[123, 456],
        size_t_single=789,
        float_array=[-1.23, 1.23],
        float_single=3.45,
        double_array=[-1.23, 1.23],
        double_single=3.45,
        string=b"abc",  # format = '2s', so 2 bytes should be saved, not 3!
        pascal_string=b"def",  # format = '2p', Should save maximum 2 bytes! (that is inclusive the 'length' byte!)
        void_pointer_array=[123, 456],
        void_pointer_single=789,
    )


@fixture
def byte_stream(data):
    fp = BytesIO()
    data.write(fp)
    fp.seek(0)

    return fp


def test_demonstration(byte_stream, data):
    obj = FullCapabilities.read(byte_stream)
    assert isinstance(obj, FullCapabilities)

    for field in fields(FullCapabilities):
        new_value = getattr(obj, field.name)
        old_value = getattr(data, field.name)

        if field.type == float:
            new_value = approx(new_value)
        elif field.type == list[float]:
            new_value = [approx(n) for n in new_value]

        assert old_value == new_value


def test_dynamic_field_length():
    @dataclass
    class DynamicFields(Block):
        length: int = "B"
        string: bytes = "{length}s"

    obj = DynamicFields(length=5, string=b"a" * 5)

    stream = BytesIO()
    obj.write(stream)
    stream.seek(0)

    assert stream.getvalue() == b"\x05aaaaa"

    stream.seek(0)
    sut = obj.read(stream)

    assert sut == obj


def test_eof():
    @dataclass
    class EOFTest(Block):
        dummy: int = "B"

    stream = BytesIO()
    with raises(EOFError):
        EOFTest.read(stream)


def test_wrong_field_order_for_dynamic_fields():
    @dataclass
    class DynamicFieldsWrongOrder(Block):
        string: bytes = "{length}s"
        length: int = "B"

    obj = DynamicFieldsWrongOrder(length=5, string=b"a" * 5)

    with raises(
        KeyError,
        match=r"Unknown value 'length' for field string. This replacement value should be mentioned \*before\* the current field\.",
    ):
        obj.write(BytesIO())

    stream = BytesIO(b"ab\x02")
    with raises(
        KeyError,
        match=r"Unknown value 'length' for field string. This replacement value should be mentioned \*before\* the current field\.",
    ):
        obj.read(stream)


def test_wrong_identifier():
    @dataclass
    class UnknownField(Block):
        sut: bytes = "2Z"

    with raises(ValueError, match=r"Field sut has an invalid \(or currently unsupported\) default: '2Z'"):
        UnknownField.read(BytesIO())

    with raises(ValueError, match=r"Field sut has an invalid \(or currently unsupported\) default: '2Z'"):
        UnknownField(b"ab").write(BytesIO())


def test_wrong_dynamic_identifier():
    @dataclass
    class UnknownDynamicField(Block):
        length: int = "H"
        sut: bytes = "{length}Z"

    with raises(
        ValueError,
        match=r"Field sut has an invalid \(or currently unsupported\) default: '{length}Z' \(calculated: 2Z\)",
    ):
        UnknownDynamicField.read_le(BytesIO(b"\x02\x00ab"))

    with raises(
        ValueError,
        match=r"Field sut has an invalid \(or currently unsupported\) default: '{length}Z' \(calculated: 2Z\)",
    ):
        UnknownDynamicField(length=2, sut=b"ab").write(BytesIO())


def test_wrong_field_specification():
    @dataclass
    class SomeBlob(Block):
        length: list[int] = "2HH"

    with raises(
        AssertionError,
        match=r"I can only understand either a count, or a repeat, but not '2HH'. Please write this as 3H instead.",
    ):
        SomeBlob.read_le(BytesIO(b"\x02\x00\x02\x00\x02\x00"))

    with raises(
        AssertionError,
        match=r"I can only understand either a count, or a repeat, but not '2HH'. Please write this as 3H instead.",
    ):
        SomeBlob(length=[2, 2, 2]).write(BytesIO())


def test_have_repeating_field():
    @dataclass
    class SomeBlob(Block):
        length: list[int] = "HH"

    compare_to = SomeBlob(length=[2, 2])
    obj = SomeBlob.read_le(BytesIO(b"\x02\x00\x02\x00\x02\x00"))
    assert obj == compare_to

    stream = BytesIO()
    compare_to.write_le(stream)
    stream.seek(0)
    assert stream.getvalue() == b"\x02\x00\x02\x00"


def test_have_zero_length_field():
    @dataclass
    class SomeBlob(Block):
        length: list[int] = "0H"
        string: bytes = "2s"

    compare_to = SomeBlob(length=[], string=b"ab")
    obj = SomeBlob.read_be(BytesIO(b"abc"))
    assert obj == compare_to

    stream = BytesIO()
    compare_to.write_be(stream)
    stream.seek(0)
    assert stream.getvalue() == b"ab"


def test_different_encodings():
    @dataclass
    class SomeBlob(Block):
        length: int = "H"

    le_obj = SomeBlob(length=2)
    be_obj = SomeBlob(length=512)

    assert SomeBlob.read(BytesIO(b"\x02\x00")) == le_obj
    assert SomeBlob.read_native_standard(BytesIO(b"\x02\x00")) == le_obj

    assert SomeBlob.read_le(BytesIO(b"\x02\x00")) == le_obj
    assert SomeBlob.read_little_endian(BytesIO(b"\x02\x00")) == le_obj

    assert SomeBlob.read_be(BytesIO(b"\x02\x00")) == be_obj
    assert SomeBlob.read_big_endian(BytesIO(b"\x02\x00")) == be_obj
    assert SomeBlob.read_network(BytesIO(b"\x02\x00")) == be_obj

    def assert_method(obj: SomeBlob, method: str, expected: bytes):
        stream = BytesIO()
        getattr(obj, method)(stream)
        assert stream.getvalue() == expected

    assert_method(le_obj, "write", b"\x02\x00")
    assert_method(le_obj, "write_native_standard", b"\x02\x00")

    assert_method(le_obj, "write_le", b"\x02\x00")
    assert_method(le_obj, "write_little_endian", b"\x02\x00")
    assert_method(le_obj, "write_be", b"\x00\x02")
    assert_method(le_obj, "write_big_endian", b"\x00\x02")
    assert_method(le_obj, "write_network", b"\x00\x02")
