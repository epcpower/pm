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
        signed=True,
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


def try_loading_multiplex():
    import io
    f = io.BytesIO(textwrap.dedent('''\
    {SEND}
    
    [TestMultiplexedMessage]
    ID=1FFFFFFFh
    Type=Extended
    DLC=0
    Mux=MuxA 0,8 0
    Var=SignalA unsigned 0,0
    
    [TestMultiplexedMessage]
    DLC=0
    Mux=MuxB 0,8 1
    Var=SignalB signed 0,0
    ''').encode('utf-8'))
    import canmatrix
    matrix, = canmatrix.formats.load(
        fileObject=f,
        importType='sym',
    ).values()

    print()


def tidy_sym(s):
    return '\n'.join(s.strip() for s in s.splitlines()).strip()


def test_multiplexed():
    root = epcpm.symbolmodel.Root()
    builder = epcpm.symbolstosym.builders.wrap(root)

    multiplexed_message = epcpm.symbolmodel.MultiplexedMessage(
        name='Test Multiplexed Message',
        identifier='0xbabeface',
    )
    root.append_child(multiplexed_message)

    expected = textwrap.dedent('''\
    FormatVersion=5.0 // Do not edit this line!
    Title="canmatrix-Export"
    {ENUMS}


    {SENDRECEIVE}

    [TestMultiplexedMessage]
    ID=BABEFACEh
    Type=Extended
    DLC=0
    ''')

    # assert tidy_sym(builder.gen()) == tidy_sym(expected)

    multiplex_signal = epcpm.symbolmodel.Signal(
        name='Multiplexer Signal',
        bits=8,
    )
    multiplexed_message.append_child(multiplex_signal)
    common_signal = epcpm.symbolmodel.Signal(
        name='Common Signal',
        signed=True,
    )
    multiplexed_message.append_child(common_signal)

    # seems like at this point it should do the same thing, or perhaps
    # add a line for the multiplexer signal.  instead it wipes the message
    # out entirely.
    # expected += textwrap.dedent('''\
    # Mux=MultiplexerSignal0 0,8 0
    # Var=CommonSignal signed 0,0
    # ''')
    # assert tidy_sym(builder.gen()) == tidy_sym(expected)

    multiplexer_a = epcpm.symbolmodel.Multiplexer(
        name='Test Multiplexer A',
        identifier=1,
    )
    multiplexed_message.append_child(multiplexer_a)
    signal_a = epcpm.symbolmodel.Signal(
        name='Signal A',
        signed=True,
    )
    multiplexer_a.append_child(signal_a)

    expected += textwrap.dedent('''\
    Mux=TestMultiplexerA 0,8 1
    Var=CommonSignal signed 0,0
    Var=SignalA signed 0,0
    ''')

    assert tidy_sym(builder.gen()) == tidy_sym(expected)

    multiplexer_b = epcpm.symbolmodel.Multiplexer(
        name='Test Multiplexer B',
        identifier=2,
    )
    multiplexed_message.append_child(multiplexer_b)
    signal_b = epcpm.symbolmodel.Signal(
        name='Signal B',
        signed=True,
    )
    multiplexer_b.append_child(signal_b)

    expected += textwrap.dedent('''\

    [TestMultiplexedMessage]
    DLC=0
    Mux=TestMultiplexerB 0,8 2
    Var=CommonSignal signed 0,0
    Var=SignalB signed 0,0
    ''')

    assert tidy_sym(builder.gen()) == tidy_sym(expected)


def test_enumerations():
    project = epcpm.project.create_blank()
    parameter_root = project.models.parameters.root
    symbol_root = project.models.symbols.root

    builder = epcpm.symbolstosym.builders.wrap(
        symbol_root,
        parameter_uuid_finder=project.models.symbols.node_from_uuid,
        parameter_model=project.models.parameters,
    )

    on_off = epcpm.parametermodel.Enumeration(name='On Off')
    parameter_root.append_child(on_off)
    off = epcpm.parametermodel.Enumerator(name='off', value=0)
    on = epcpm.parametermodel.Enumerator(name='on', value=1)

    on_off.append_child(off)
    on_off.append_child(on)

    parameter = epcpm.parametermodel.EnumeratedParameter(
        enumeration_uuid=on_off.uuid,
    )
    parameter_root.append_child(parameter)

    message = epcpm.symbolmodel.Message()
    symbol_root.append_child(message)
    signal = epcpm.symbolmodel.Signal(
        parameter_uuid=parameter.uuid,
    )
    message.append_child(signal)

    expected = textwrap.dedent('''\
    FormatVersion=5.0 // Do not edit this line!
    Title="canmatrix-Export"
    {ENUMS}
    enum OnOff(0="off", 1="on")
    
    {SENDRECEIVE}
    
    [NewMessage]
    ID=1FFFFFFFh
    Type=Extended
    DLC=0
    Var=NewSignal unsigned 0,0 /e:OnOff
    ''')

    assert tidy_sym(builder.gen()) == tidy_sym(expected)
