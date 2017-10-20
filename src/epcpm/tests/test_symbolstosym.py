import textwrap

import epcpm.symbolmodel
import epcpm.symbolstosym


def test_explore():
    root = epcpm.symbolmodel.Root()

    message = epcpm.symbolmodel.Message(
        name='Test Message',
    )
    root.append_child(message)

    signal = epcpm.symbolmodel.Signal(
        name='Test Signal',
    )
    message.append_child(signal)

    builder = epcpm.symbolstosym.builders.wrap(root)
    s = builder.gen()

    assert s == textwrap.dedent('''\
    FormatVersion=5.0 // Do not edit this line!
    Title="canmatrix-Export"
    {ENUMS}


    {SENDRECEIVE}

    [TestMessage]
    ID=1FFFFFFFh
    Type=Extended
    DLC=0
    Var=TestSignal signed 0,0

    ''')
