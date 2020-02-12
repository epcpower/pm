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
        identifier=0x1abeface,
    )
    root.append_child(multiplexed_message)

    expected = textwrap.dedent('''\
    FormatVersion=5.0 // Do not edit this line!
    Title="canmatrix-Export"
    {ENUMS}


    {SENDRECEIVE}

    [TestMultiplexedMessage]
    ID=1ABEFACEh
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
    Var=CommonSignal signed 0,0 /d:0
    Var=SignalA signed 0,0 /d:0 /ln:"New Parameter"	// <rw:1:1>  <uuid:c56650d0-252d-4b88-a645-fecd23dda1b6>
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
    Var=CommonSignal signed 0,0 /d:0
    Var=SignalB signed 0,0 /d:0 /ln:"New Parameter"	// <rw:1:1>  <uuid:c6956fa5-15cc-48f4-a0a7-c4b691f14fec>
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

    parameter = epyqlib.pm.parametermodel.Parameter(
        uuid='29cf3408-043e-4573-a511-0c7638688663',
    )
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
    Var=NewSignal unsigned 0,0 /e:OnOff /d:0 /ln:"New Parameter"	// <rw:1:1>  <uuid:29cf3408-043e-4573-a511-0c7638688663>
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
    Var=FactorySignal unsigned 0,0 /d:0 /ln:"Factory Parameter"	// <rw:1:1> <factory>  <uuid:40477147-cd0b-407a-9dc1-805d3205214b>
    Var=AccessSignal unsigned 0,0 /e:AccessLevel /d:0 /ln:"Access Parameter"	// <rw:1:1>  <uuid:908f42e7-7632-47bc-a8c7-eb1eca4e277c>
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
    Var=AO_0 unsigned 16,8 /d:0 /ln:"AO_0"	// <rw:1:1>  <uuid:715a25f9-39d3-4410-9f1f-119991ab2468>
    Var=AO_1 unsigned 24,8 /d:0 /ln:"AO_1"	// <rw:1:1>  <uuid:e1655e93-0f2a-45d8-b881-70e697e485f4>
    
    [Tables]
    DLC=8
    Mux=First TableEO_0ET_0_ArrayTwo_A 0,8 6 	// <table>
    Var=AT_0 unsigned 16,16 /d:0 /ln:"AT_0"	// <rw:1:1>  <uuid:a02b02ae-b430-490b-a8bf-a32d976fb35d>
    Var=AT_1 unsigned 32,16 /d:0 /ln:"AT_1"	// <rw:1:1>  <uuid:1999bee0-358a-475c-a122-c6171bfadf9a>
    Var=AT_2 unsigned 48,16 /d:0 /ln:"AT_2"	// <rw:1:1>  <uuid:7f41fcc0-d421-4dbd-a5d7-abac4cc3c868>
    
    [Tables]
    DLC=8
    Mux=First TableEO_0ET_0_ArrayTwo_B 0,8 7 	// <table>
    Var=AT_3 unsigned 16,16 /d:0 /ln:"AT_3"	// <rw:1:1>  <uuid:cc090c3e-ceac-4b6c-8b8d-d9a1fed5c80b>
    Var=AT_4 unsigned 32,16 /d:0 /ln:"AT_4"	// <rw:1:1>  <uuid:e887a919-2fe1-4801-a745-1b73b3032cfe>
    
    [Tables]
    DLC=8
    Mux=First TableEO_0ET_1_ArrayOne 0,8 8 	// <table>
    Var=AO_0 unsigned 16,8 /d:0 /ln:"AO_0"	// <rw:1:1>  <uuid:12889ce7-fa95-4707-bee1-e1db71330427>
    Var=AO_1 unsigned 24,8 /d:0 /ln:"AO_1"	// <rw:1:1>  <uuid:3366c5b9-0208-4c5e-818f-a72f0879f2cd>
    
    [Tables]
    DLC=8
    Mux=First TableEO_0ET_1_ArrayTwo_A 0,8 9 	// <table>
    Var=AT_0 unsigned 16,16 /d:0 /ln:"AT_0"	// <rw:1:1>  <uuid:9a89ce3e-be35-4905-8f93-fd29f952fde0>
    Var=AT_1 unsigned 32,16 /d:0 /ln:"AT_1"	// <rw:1:1>  <uuid:d2300447-d35d-4057-b37f-81da3a981378>
    Var=AT_2 unsigned 48,16 /d:0 /ln:"AT_2"	// <rw:1:1>  <uuid:68e82189-2b3b-429e-8bb7-36f6f800cce8>
    
    [Tables]
    DLC=8
    Mux=First TableEO_0ET_1_ArrayTwo_B 0,8 0Ah	// <table>
    Var=AT_3 unsigned 16,16 /d:0 /ln:"AT_3"	// <rw:1:1>  <uuid:7692c837-1e3f-4319-b4b7-4845cb6a9e3f>
    Var=AT_4 unsigned 32,16 /d:0 /ln:"AT_4"	// <rw:1:1>  <uuid:b8df3096-0051-4487-a819-d6c8c22328bc>
    
    [Tables]
    DLC=8
    Mux=First TableEO_0ET_2_ArrayOne 0,8 0Bh	// <table>
    Var=AO_0 unsigned 16,8 /d:0 /ln:"AO_0"	// <rw:1:1>  <uuid:7fc6837c-6f99-4980-9716-04fe088911a0>
    Var=AO_1 unsigned 24,8 /d:0 /ln:"AO_1"	// <rw:1:1>  <uuid:d53144c4-e5c7-47fd-8b82-caf617173dd5>
    
    [Tables]
    DLC=8
    Mux=First TableEO_0ET_2_ArrayTwo_A 0,8 0Ch	// <table>
    Var=AT_0 unsigned 16,16 /d:0 /ln:"AT_0"	// <rw:1:1>  <uuid:643978e1-b2fe-4f5a-bcf6-a55c7f4e8330>
    Var=AT_1 unsigned 32,16 /d:0 /ln:"AT_1"	// <rw:1:1>  <uuid:40b9f544-93e7-4cdc-ac37-251948cd8e99>
    Var=AT_2 unsigned 48,16 /d:0 /ln:"AT_2"	// <rw:1:1>  <uuid:29fd4dd1-1422-4f20-bf23-f15f4ee767f4>
    
    [Tables]
    DLC=8
    Mux=First TableEO_0ET_2_ArrayTwo_B 0,8 0Dh	// <table>
    Var=AT_3 unsigned 16,16 /d:0 /ln:"AT_3"	// <rw:1:1>  <uuid:65f14e81-d06d-4766-bdcb-aca8a47fd913>
    Var=AT_4 unsigned 32,16 /d:0 /ln:"AT_4"	// <rw:1:1>  <uuid:d5643fa0-2c4b-42a3-89c9-5a8a623a5fdf>
    
    [Tables]
    DLC=8
    Mux=First TableEO_0ET_3_ArrayOne 0,8 0Eh	// <table>
    Var=AO_0 unsigned 16,8 /d:0 /ln:"AO_0"	// <rw:1:1>  <uuid:6da0b3b7-00c9-4a71-a7bc-2eff01d9b072>
    Var=AO_1 unsigned 24,8 /d:0 /ln:"AO_1"	// <rw:1:1>  <uuid:5052fb2e-ff2b-45ed-8eb4-8fb20fa48f4b>
    
    [Tables]
    DLC=8
    Mux=First TableEO_0ET_3_ArrayTwo_A 0,8 0Fh	// <table>
    Var=AT_0 unsigned 16,16 /d:0 /ln:"AT_0"	// <rw:1:1>  <uuid:b5f3aa12-5374-448c-b459-d82b0423da62>
    Var=AT_1 unsigned 32,16 /d:0 /ln:"AT_1"	// <rw:1:1>  <uuid:34f19371-9da8-445e-9bdc-150609c55b0b>
    Var=AT_2 unsigned 48,16 /d:0 /ln:"AT_2"	// <rw:1:1>  <uuid:cdc54427-37cf-4369-bab4-c00fa3fffe1a>
    
    [Tables]
    DLC=8
    Mux=First TableEO_0ET_3_ArrayTwo_B 0,8 10h	// <table>
    Var=AT_3 unsigned 16,16 /d:0 /ln:"AT_3"	// <rw:1:1>  <uuid:463d5adc-6dcf-4821-8dad-efc86b611693>
    Var=AT_4 unsigned 32,16 /d:0 /ln:"AT_4"	// <rw:1:1>  <uuid:9ad7eec5-2c78-496d-ab4b-f57c1d1b8bb5>
    
    [Tables]
    DLC=8
    Mux=First TableEO_1ET_0_ArrayOne 0,8 11h	// <table>
    Var=AO_0 unsigned 16,8 /d:0 /ln:"AO_0"	// <rw:1:1>  <uuid:5b3ff5fa-8a91-4bcb-a39e-3fa3b299aabd>
    Var=AO_1 unsigned 24,8 /d:0 /ln:"AO_1"	// <rw:1:1>  <uuid:50601aeb-1838-4850-a6c1-285a819fc6c6>
    
    [Tables]
    DLC=8
    Mux=First TableEO_1ET_0_ArrayTwo_A 0,8 12h	// <table>
    Var=AT_0 unsigned 16,16 /d:0 /ln:"AT_0"	// <rw:1:1>  <uuid:c3764c5c-c14c-410a-9c85-981be157a7dc>
    Var=AT_1 unsigned 32,16 /d:0 /ln:"AT_1"	// <rw:1:1>  <uuid:24450cfa-7983-4786-9e89-e59c149b3221>
    Var=AT_2 unsigned 48,16 /d:0 /ln:"AT_2"	// <rw:1:1>  <uuid:14be748b-1768-4901-8214-d83b53e37747>
    
    [Tables]
    DLC=8
    Mux=First TableEO_1ET_0_ArrayTwo_B 0,8 13h	// <table>
    Var=AT_3 unsigned 16,16 /d:0 /ln:"AT_3"	// <rw:1:1>  <uuid:22900720-f67e-45fe-bd66-abb7872d1f5e>
    Var=AT_4 unsigned 32,16 /d:0 /ln:"AT_4"	// <rw:1:1>  <uuid:154ecbc4-0f8a-421a-b9fc-12859e2ff446>
    
    [Tables]
    DLC=8
    Mux=First TableEO_1ET_1_ArrayOne 0,8 14h	// <table>
    Var=AO_0 unsigned 16,8 /d:0 /ln:"AO_0"	// <rw:1:1>  <uuid:d2cac4d4-5c94-4ec9-8ec0-e006b42e934c>
    Var=AO_1 unsigned 24,8 /d:0 /ln:"AO_1"	// <rw:1:1>  <uuid:057d1ece-477e-4f42-a19f-beb640269d2b>
    
    [Tables]
    DLC=8
    Mux=First TableEO_1ET_1_ArrayTwo_A 0,8 15h	// <table>
    Var=AT_0 unsigned 16,16 /d:0 /ln:"AT_0"	// <rw:1:1>  <uuid:0345218d-4ae2-4652-b9ae-51a1a51db725>
    Var=AT_1 unsigned 32,16 /d:0 /ln:"AT_1"	// <rw:1:1>  <uuid:a676e7ae-69ba-4ab5-abfd-d7b6d1b61028>
    Var=AT_2 unsigned 48,16 /d:0 /ln:"AT_2"	// <rw:1:1>  <uuid:7a8dafb9-a89c-4159-bad6-cf08f3d47f6d>
    
    [Tables]
    DLC=8
    Mux=First TableEO_1ET_1_ArrayTwo_B 0,8 16h	// <table>
    Var=AT_3 unsigned 16,16 /d:0 /ln:"AT_3"	// <rw:1:1>  <uuid:016c8e13-6aa4-4ead-9fbc-66e95bef7166>
    Var=AT_4 unsigned 32,16 /d:0 /ln:"AT_4"	// <rw:1:1>  <uuid:b400a484-7edf-4519-aebb-cf6681c62ad6>
    
    [Tables]
    DLC=8
    Mux=First TableEO_1ET_2_ArrayOne 0,8 17h	// <table>
    Var=AO_0 unsigned 16,8 /d:0 /ln:"AO_0"	// <rw:1:1>  <uuid:bc12e308-f351-46f2-980b-3f69c7fe5f4d>
    Var=AO_1 unsigned 24,8 /d:0 /ln:"AO_1"	// <rw:1:1>  <uuid:bc2328ef-5ba9-46bc-8680-e32c9f231e43>
    
    [Tables]
    DLC=8
    Mux=First TableEO_1ET_2_ArrayTwo_A 0,8 18h	// <table>
    Var=AT_0 unsigned 16,16 /d:0 /ln:"AT_0"	// <rw:1:1>  <uuid:73ee2f19-2254-40f0-a8f8-96daf173803d>
    Var=AT_1 unsigned 32,16 /d:0 /ln:"AT_1"	// <rw:1:1>  <uuid:36eb85a9-d8f2-4e31-96f8-a17eb15442de>
    Var=AT_2 unsigned 48,16 /d:0 /ln:"AT_2"	// <rw:1:1>  <uuid:7e8f8bd2-e4fc-46c0-9982-d9fdaae35bbd>
    
    [Tables]
    DLC=8
    Mux=First TableEO_1ET_2_ArrayTwo_B 0,8 19h	// <table>
    Var=AT_3 unsigned 16,16 /d:0 /ln:"AT_3"	// <rw:1:1>  <uuid:1b3f4f7b-e3dd-4a6b-8f57-64cfd39ffbaf>
    Var=AT_4 unsigned 32,16 /d:0 /ln:"AT_4"	// <rw:1:1>  <uuid:bd327816-1be3-47f3-8d8c-348b2b50c89c>
    
    [Tables]
    DLC=8
    Mux=First TableEO_1ET_3_ArrayOne 0,8 1Ah	// <table>
    Var=AO_0 unsigned 16,8 /d:0 /ln:"AO_0"	// <rw:1:1>  <uuid:10a65f59-fe09-41ec-9c6b-4ccd3db653be>
    Var=AO_1 unsigned 24,8 /d:0 /ln:"AO_1"	// <rw:1:1>  <uuid:dc48c013-62e7-4665-bda6-a7d1a2164000>
    
    [Tables]
    DLC=8
    Mux=First TableEO_1ET_3_ArrayTwo_A 0,8 1Bh	// <table>
    Var=AT_0 unsigned 16,16 /d:0 /ln:"AT_0"	// <rw:1:1>  <uuid:45dca7f8-1f94-49bc-9028-83acb2ceb53d>
    Var=AT_1 unsigned 32,16 /d:0 /ln:"AT_1"	// <rw:1:1>  <uuid:fc375c2d-1b0a-446e-b467-27f278e71dd0>
    Var=AT_2 unsigned 48,16 /d:0 /ln:"AT_2"	// <rw:1:1>  <uuid:61e84991-52c1-4259-b2c4-0c904ca31f0a>
    
    [Tables]
    DLC=8
    Mux=First TableEO_1ET_3_ArrayTwo_B 0,8 1Ch	// <table>
    Var=AT_3 unsigned 16,16 /d:0 /ln:"AT_3"	// <rw:1:1>  <uuid:38edbaee-7580-41a8-82f0-9da8f494fb43>
    Var=AT_4 unsigned 32,16 /d:0 /ln:"AT_4"	// <rw:1:1>  <uuid:baed5be3-d32f-455b-aff4-4a353b28400b>
    ''')

    assert tidy_sym(result) == tidy_sym(expected)
