import textwrap

import epyqlib.attrsmodel
import epyqlib.pm.parametermodel

import epcpm.canmodel
import epcpm.cantosym


# def test_explore():
#     root = epcpm.canmodel.Root()
#
#     message = epcpm.canmodel.Message(
#         name='Test Message',
#     )
#     root.append_child(message)
#
#     signal = epcpm.canmodel.Signal(
#         name='Test Signal',
#         signed=True,
#     )
#     message.append_child(signal)
#
#     builder = epcpm.cantosym.builders.wrap(root)
#     s = builder.gen()
#
#     assert s == textwrap.dedent('''\
#     FormatVersion=5.0 // Do not edit this line!
#     Title="canmatrix-Export"
#     {ENUMS}
#
#
#     {SENDRECEIVE}
#
#     [TestMessage]
#     ID=1FFFFFFFh
#     Type=Extended
#     DLC=0
#     Var=TestSignal signed 0,0
#
#     ''')


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
    root = epcpm.canmodel.Root()

    parameter_root = epyqlib.pm.parametermodel.Root()
    model = epyqlib.attrsmodel.Model(
        root=parameter_root,
        columns=epyqlib.pm.parametermodel.columns,
    )
    model.add_drop_sources(model.root)
    access_levels = epyqlib.pm.parametermodel.AccessLevels()
    access_level = epyqlib.pm.parametermodel.AccessLevel(value=0)
    access_levels.append_child(access_level)
    enumerations = epyqlib.pm.parametermodel.Enumerations()
    enumerations.append_child(access_levels)
    parameter_root.append_child(enumerations)
    builder = epcpm.cantosym.builders.wrap(
        wrapped=root,
        parameter_uuid_finder=model.node_from_uuid,
        parameter_model=model,
        access_levels=access_levels,
    )

    multiplexed_message = epcpm.canmodel.MultiplexedMessage(
        name='Test Multiplexed Message',
        identifier=0xbabeface,
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

    multiplex_signal = epcpm.canmodel.Signal(
        name='Multiplexer Signal',
        bits=8,
    )
    multiplexed_message.append_child(multiplex_signal)
    common_signal = epcpm.canmodel.Signal(
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

    parameter_a = epyqlib.pm.parametermodel.Parameter()
    parameter_root.append_child(parameter_a)

    multiplexer_a = epcpm.canmodel.Multiplexer(
        name='Test Multiplexer A',
        identifier=1,
    )
    multiplexed_message.append_child(multiplexer_a)
    signal_a = epcpm.canmodel.Signal(
        name='Signal A',
        signed=True,
        parameter_uuid=parameter_a.uuid,
    )
    multiplexer_a.append_child(signal_a)

    expected += textwrap.dedent('''\
    Mux=TestMultiplexerA 0,8 1
    Var=CommonSignal signed 0,0
    Var=SignalA signed 0,0 /ln:"New Parameter"
    ''')

    assert tidy_sym(builder.gen()) == tidy_sym(expected)

    parameter_b = epyqlib.pm.parametermodel.Parameter()
    parameter_root.append_child(parameter_b)

    multiplexer_b = epcpm.canmodel.Multiplexer(
        name='Test Multiplexer B',
        identifier=2,
    )
    multiplexed_message.append_child(multiplexer_b)
    signal_b = epcpm.canmodel.Signal(
        name='Signal B',
        signed=True,
        parameter_uuid=parameter_b.uuid,
    )
    multiplexer_b.append_child(signal_b)

    expected += textwrap.dedent('''\

    [TestMultiplexedMessage]
    DLC=0
    Mux=TestMultiplexerB 0,8 2
    Var=CommonSignal signed 0,0
    Var=SignalB signed 0,0 /ln:"New Parameter"
    ''')

    assert tidy_sym(builder.gen()) == tidy_sym(expected)


def test_enumerations():
    project = epcpm.project.create_blank()
    parameter_root = project.models.parameters.root
    access_levels = epyqlib.pm.parametermodel.AccessLevels()
    access_level = epyqlib.pm.parametermodel.AccessLevel(value=0)
    access_levels.append_child(access_level)
    enumerations = epyqlib.pm.parametermodel.Enumerations()
    enumerations.append_child(access_levels)
    parameter_root.append_child(enumerations)
    can_root = project.models.can.root

    builder = epcpm.cantosym.builders.wrap(
        can_root,
        parameter_uuid_finder=project.models.can.node_from_uuid,
        parameter_model=project.models.parameters,
        access_levels=access_levels,
    )

    on_off = epyqlib.pm.parametermodel.Enumeration(name='On Off')
    parameter_root.append_child(on_off)
    off = epyqlib.pm.parametermodel.Enumerator(name='off', value=0)
    on = epyqlib.pm.parametermodel.Enumerator(name='on', value=1)

    on_off.append_child(off)
    on_off.append_child(on)

    parameter = epyqlib.pm.parametermodel.Parameter(
        enumeration_uuid=on_off.uuid,
    )
    parameter_root.append_child(parameter)

    message = epcpm.canmodel.Message()
    can_root.append_child(message)
    signal = epcpm.canmodel.Signal(
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
    Var=NewSignal unsigned 0,0 /e:OnOff /ln:"New Parameter"
    ''')

    assert tidy_sym(builder.gen()) == tidy_sym(expected)


def test_access_level():
    project = epcpm.project.create_blank()
    parameter_root = project.models.parameters.root
    can_root = project.models.can.root

    access_levels = epyqlib.pm.parametermodel.AccessLevels(
        name='AccessLevel',
        uuid='54bb11bb-a39d-4b30-a597-da3fbeda4d7a',
    )

    builder = epcpm.cantosym.builders.wrap(
        can_root,
        parameter_uuid_finder=project.models.can.node_from_uuid,
        parameter_model=project.models.parameters,
        access_levels=access_levels,
    )

    user = epyqlib.pm.parametermodel.Enumerator(
        name='user',
        value=0,
        uuid='b4c58cf9-3705-4e73-8e31-09f8da22ff61',
    )
    factory = epyqlib.pm.parametermodel.Enumerator(
        name='factory',
        value=1,

    )

    access_levels.append_child(user)
    access_levels.append_child(factory)

    enumerations = epyqlib.pm.parametermodel.Enumerations(
        name='Enumerations',
        uuid='1936c213-5230-454a-81f9-c8099046a19d',
    )
    parameter_root.append_child(enumerations)

    enumerations.append_child(access_levels)

    parameter = epyqlib.pm.parametermodel.Parameter(
        name='Factory Parameter',
        access_level_uuid=factory.uuid,
        uuid='40477147-cd0b-407a-9dc1-805d3205214b',
    )
    parameter_root.append_child(parameter)

    access_level_parameter = epyqlib.pm.parametermodel.Parameter(
        name='Access Parameter',
        enumeration_uuid=access_levels.uuid,
        uuid='908f42e7-7632-47bc-a8c7-eb1eca4e277c',
    )
    parameter_root.append_child(access_level_parameter)

    message = epcpm.canmodel.Message(

    )
    can_root.append_child(message)
    signal = epcpm.canmodel.Signal(
        name='Factory Signal',
        parameter_uuid=parameter.uuid,
        uuid='07047416-73e3-48bd-8c0c-85c1de078200',
    )
    message.append_child(signal)

    access_level_signal = epcpm.canmodel.Signal(
        name='Access Signal',
        parameter_uuid=access_level_parameter.uuid,
        uuid='4f62704f-6548-4f80-b7b7-702f214a394b',
    )
    message.append_child(access_level_signal)

    expected = textwrap.dedent('''\
    FormatVersion=5.0 // Do not edit this line!
    Title="canmatrix-Export"
    {ENUMS}
    enum AccessLevel(0="user", 1="factory")

    {SENDRECEIVE}

    [NewMessage]
    ID=1FFFFFFFh
    Type=Extended
    DLC=0
    Var=FactorySignal unsigned 0,0 /ln:"Factory Parameter"	// <factory>
    Var=AccessSignal unsigned 0,0 /e:AccessLevel /ln:"Access Parameter"
    ''')

    assert tidy_sym(builder.gen()) == tidy_sym(expected)
