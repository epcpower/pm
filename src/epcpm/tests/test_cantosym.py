import pathlib
import textwrap

import epyqlib.attrsmodel
import epyqlib.pm.parametermodel

import epcpm.canmodel
import epcpm.cantosym
import epcpm.project


here = pathlib.Path(__file__).parent


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

    parameter_root = epyqlib.pm.parametermodel.Root(
        uuid='5ad34154-f585-40bc-992a-0c9685cbdb26',
    )
    model = epyqlib.attrsmodel.Model(
        root=parameter_root,
        columns=epyqlib.pm.parametermodel.columns,
    )
    model.add_drop_sources(model)
    access_levels = epyqlib.pm.parametermodel.AccessLevels(
        uuid='284090fd-6893-4800-92bc-035dbf25909c',
    )
    access_level = epyqlib.pm.parametermodel.AccessLevel(
        value=0,
        uuid='40ced595-a5f3-41ee-9156-eb0ac343c9a5',
    )
    access_levels.append_child(access_level)
    enumerations = epyqlib.pm.parametermodel.Enumerations(
        uuid='af9bfcf3-1858-4fb9-b238-a7641bcffcd4',
    )
    enumerations.append_child(access_levels)
    parameter_root.append_child(enumerations)
    builder = epcpm.cantosym.builders.wrap(
        wrapped=root,
        parameter_uuid_finder=model.node_from_uuid,
        parameter_model=model,
        access_levels=access_levels,
    )

    multiplexed_message = epcpm.canmodel.MultiplexedMessage(
        name='TestMultiplexedMessage',
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
        name='MultiplexerSignal',
        bits=8,
        uuid='c812b3be-c883-4828-8695-0f61db24fde3',
    )
    multiplexed_message.append_child(multiplex_signal)
    common_signal = epcpm.canmodel.Signal(
        name='CommonSignal',
        signed=True,
        uuid='3ecc047e-e88c-4917-b22c-2751db6db705',
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

    parameter_a = epyqlib.pm.parametermodel.Parameter(
        uuid='c56650d0-252d-4b88-a645-fecd23dda1b6',
    )
    parameter_root.append_child(parameter_a)

    multiplexer_a = epcpm.canmodel.Multiplexer(
        name='TestMultiplexerA',
        identifier=1,
        uuid='bc872648-94d2-4bee-8a4f-5654cac93d38',
    )
    multiplexed_message.append_child(multiplexer_a)
    signal_a = epcpm.canmodel.Signal(
        name='SignalA',
        signed=True,
        parameter_uuid=parameter_a.uuid,
        uuid='cc5a8db2-b3da-4f2e-b8c6-83569b9c6824',
    )
    multiplexer_a.append_child(signal_a)

    expected += textwrap.dedent('''\
    Mux=TestMultiplexerA 0,8 1
    Var=CommonSignal signed 0,0
    Var=SignalA signed 0,0 /ln:"New Parameter"
    ''')

    assert tidy_sym(builder.gen()) == tidy_sym(expected)

    parameter_b = epyqlib.pm.parametermodel.Parameter(
        uuid='c6956fa5-15cc-48f4-a0a7-c4b691f14fec',
    )
    parameter_root.append_child(parameter_b)

    multiplexer_b = epcpm.canmodel.Multiplexer(
        name='TestMultiplexerB',
        identifier=2,
        uuid='7efd7e89-71f8-400b-b11d-7f49642309f8',
    )
    multiplexed_message.append_child(multiplexer_b)
    signal_b = epcpm.canmodel.Signal(
        name='SignalB',
        signed=True,
        parameter_uuid=parameter_b.uuid,
        uuid='b69c211b-0e0c-4ba1-947e-ea47a1baf11d',
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

    on_off = epyqlib.pm.parametermodel.Enumeration(name='OnOff')
    parameter_root.append_child(on_off)
    off = epyqlib.pm.parametermodel.Enumerator(name='off', value=0)
    on = epyqlib.pm.parametermodel.Enumerator(name='on', value=1)

    on_off.append_child(off)
    on_off.append_child(on)

    parameter = epyqlib.pm.parametermodel.Parameter()
    parameter_root.append_child(parameter)

    message = epcpm.canmodel.Message()
    can_root.append_child(message)
    signal = epcpm.canmodel.Signal(
        enumeration_uuid=on_off.uuid,
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
        uuid='f5dc405f-a0ed-4590-9553-bf3f1efec23a',
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
        uuid='908f42e7-7632-47bc-a8c7-eb1eca4e277c',
    )
    parameter_root.append_child(access_level_parameter)

    message = epcpm.canmodel.Message(

    )
    can_root.append_child(message)
    signal = epcpm.canmodel.Signal(
        name='FactorySignal',
        parameter_uuid=parameter.uuid,
        uuid='07047416-73e3-48bd-8c0c-85c1de078200',
    )
    message.append_child(signal)

    access_level_signal = epcpm.canmodel.Signal(
        name='AccessSignal',
        parameter_uuid=access_level_parameter.uuid,
        enumeration_uuid=access_levels.uuid,
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


def test_table():
    project = epcpm.project.loadp(here/'project'/'project.pmp')
    can_table, = project.models.can.root.nodes_by_attribute(
        attribute_value='First Table',
        attribute_name='name',
    )
    access_levels, = project.models.parameters.root.nodes_by_attribute(
        attribute_value='AccessLevel',
        attribute_name='name',
    )
    parameter_table = project.models.parameters.node_from_uuid(
        can_table.table_uuid,
    )
    parameter_table.update()

    can_table.update()

    builder = epcpm.cantosym.builders.wrap(
        project.models.can.root,
        parameter_uuid_finder=project.models.can.node_from_uuid,
        parameter_model=project.models.parameters,
        access_levels=access_levels,
    )

    result = builder.gen()
    print(result)

    expected = textwrap.dedent('''\
    FormatVersion=5.0 // Do not edit this line!
    Title="canmatrix-Export"
    {ENUMS}
    
    
    {SENDRECEIVE}
    
    [Tables]
    ID=1FFFFFFFh
    Type=Extended
    DLC=8
    Mux=First TableEO_0ET_0_ArrayOne 0,8 5 	// <table>
    Var=AO_0 unsigned 16,8 /ln:"AO_0"
    Var=AO_1 unsigned 24,8 /ln:"AO_1"
    
    [Tables]
    DLC=8
    Mux=First TableEO_0ET_0_ArrayTwo_A 0,8 6 	// <table>
    Var=AT_0 unsigned 16,16 /ln:"AT_0"
    Var=AT_1 unsigned 32,16 /ln:"AT_1"
    Var=AT_2 unsigned 48,16 /ln:"AT_2"
    
    [Tables]
    DLC=8
    Mux=First TableEO_0ET_0_ArrayTwo_B 0,8 7 	// <table>
    Var=AT_3 unsigned 16,16 /ln:"AT_3"
    Var=AT_4 unsigned 32,16 /ln:"AT_4"
    
    [Tables]
    DLC=8
    Mux=First TableEO_0ET_1_ArrayOne 0,8 8 	// <table>
    Var=AO_0 unsigned 16,8 /ln:"AO_0"
    Var=AO_1 unsigned 24,8 /ln:"AO_1"
    
    [Tables]
    DLC=8
    Mux=First TableEO_0ET_1_ArrayTwo_A 0,8 9 	// <table>
    Var=AT_0 unsigned 16,16 /ln:"AT_0"
    Var=AT_1 unsigned 32,16 /ln:"AT_1"
    Var=AT_2 unsigned 48,16 /ln:"AT_2"
    
    [Tables]
    DLC=8
    Mux=First TableEO_0ET_1_ArrayTwo_B 0,8 0Ah	// <table>
    Var=AT_3 unsigned 16,16 /ln:"AT_3"
    Var=AT_4 unsigned 32,16 /ln:"AT_4"
    
    [Tables]
    DLC=8
    Mux=First TableEO_0ET_2_ArrayOne 0,8 0Bh	// <table>
    Var=AO_0 unsigned 16,8 /ln:"AO_0"
    Var=AO_1 unsigned 24,8 /ln:"AO_1"
    
    [Tables]
    DLC=8
    Mux=First TableEO_0ET_2_ArrayTwo_A 0,8 0Ch	// <table>
    Var=AT_0 unsigned 16,16 /ln:"AT_0"
    Var=AT_1 unsigned 32,16 /ln:"AT_1"
    Var=AT_2 unsigned 48,16 /ln:"AT_2"
    
    [Tables]
    DLC=8
    Mux=First TableEO_0ET_2_ArrayTwo_B 0,8 0Dh	// <table>
    Var=AT_3 unsigned 16,16 /ln:"AT_3"
    Var=AT_4 unsigned 32,16 /ln:"AT_4"
    
    [Tables]
    DLC=8
    Mux=First TableEO_0ET_3_ArrayOne 0,8 0Eh	// <table>
    Var=AO_0 unsigned 16,8 /ln:"AO_0"
    Var=AO_1 unsigned 24,8 /ln:"AO_1"
    
    [Tables]
    DLC=8
    Mux=First TableEO_0ET_3_ArrayTwo_A 0,8 0Fh	// <table>
    Var=AT_0 unsigned 16,16 /ln:"AT_0"
    Var=AT_1 unsigned 32,16 /ln:"AT_1"
    Var=AT_2 unsigned 48,16 /ln:"AT_2"
    
    [Tables]
    DLC=8
    Mux=First TableEO_0ET_3_ArrayTwo_B 0,8 10h	// <table>
    Var=AT_3 unsigned 16,16 /ln:"AT_3"
    Var=AT_4 unsigned 32,16 /ln:"AT_4"
    
    [Tables]
    DLC=8
    Mux=First TableEO_1ET_0_ArrayOne 0,8 11h	// <table>
    Var=AO_0 unsigned 16,8 /ln:"AO_0"
    Var=AO_1 unsigned 24,8 /ln:"AO_1"
    
    [Tables]
    DLC=8
    Mux=First TableEO_1ET_0_ArrayTwo_A 0,8 12h	// <table>
    Var=AT_0 unsigned 16,16 /ln:"AT_0"
    Var=AT_1 unsigned 32,16 /ln:"AT_1"
    Var=AT_2 unsigned 48,16 /ln:"AT_2"
    
    [Tables]
    DLC=8
    Mux=First TableEO_1ET_0_ArrayTwo_B 0,8 13h	// <table>
    Var=AT_3 unsigned 16,16 /ln:"AT_3"
    Var=AT_4 unsigned 32,16 /ln:"AT_4"
    
    [Tables]
    DLC=8
    Mux=First TableEO_1ET_1_ArrayOne 0,8 14h	// <table>
    Var=AO_0 unsigned 16,8 /ln:"AO_0"
    Var=AO_1 unsigned 24,8 /ln:"AO_1"
    
    [Tables]
    DLC=8
    Mux=First TableEO_1ET_1_ArrayTwo_A 0,8 15h	// <table>
    Var=AT_0 unsigned 16,16 /ln:"AT_0"
    Var=AT_1 unsigned 32,16 /ln:"AT_1"
    Var=AT_2 unsigned 48,16 /ln:"AT_2"
    
    [Tables]
    DLC=8
    Mux=First TableEO_1ET_1_ArrayTwo_B 0,8 16h	// <table>
    Var=AT_3 unsigned 16,16 /ln:"AT_3"
    Var=AT_4 unsigned 32,16 /ln:"AT_4"
    
    [Tables]
    DLC=8
    Mux=First TableEO_1ET_2_ArrayOne 0,8 17h	// <table>
    Var=AO_0 unsigned 16,8 /ln:"AO_0"
    Var=AO_1 unsigned 24,8 /ln:"AO_1"
    
    [Tables]
    DLC=8
    Mux=First TableEO_1ET_2_ArrayTwo_A 0,8 18h	// <table>
    Var=AT_0 unsigned 16,16 /ln:"AT_0"
    Var=AT_1 unsigned 32,16 /ln:"AT_1"
    Var=AT_2 unsigned 48,16 /ln:"AT_2"
    
    [Tables]
    DLC=8
    Mux=First TableEO_1ET_2_ArrayTwo_B 0,8 19h	// <table>
    Var=AT_3 unsigned 16,16 /ln:"AT_3"
    Var=AT_4 unsigned 32,16 /ln:"AT_4"
    
    [Tables]
    DLC=8
    Mux=First TableEO_1ET_3_ArrayOne 0,8 1Ah	// <table>
    Var=AO_0 unsigned 16,8 /ln:"AO_0"
    Var=AO_1 unsigned 24,8 /ln:"AO_1"
    
    [Tables]
    DLC=8
    Mux=First TableEO_1ET_3_ArrayTwo_A 0,8 1Bh	// <table>
    Var=AT_0 unsigned 16,16 /ln:"AT_0"
    Var=AT_1 unsigned 32,16 /ln:"AT_1"
    Var=AT_2 unsigned 48,16 /ln:"AT_2"
    
    [Tables]
    DLC=8
    Mux=First TableEO_1ET_3_ArrayTwo_B 0,8 1Ch	// <table>
    Var=AT_3 unsigned 16,16 /ln:"AT_3"
    Var=AT_4 unsigned 32,16 /ln:"AT_4"
    ''')

    assert tidy_sym(result) == tidy_sym(expected)
