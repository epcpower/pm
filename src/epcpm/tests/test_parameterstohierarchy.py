import epcpm.parametermodel
import epcpm.parameterstohierarchy
import epcpm.symbolmodel


def test_():
    parameter_root = epcpm.parametermodel.Root()

    parameters = epcpm.parametermodel.Group(name='Parameters')
    parameter_root.append_child(parameters)

    group = epcpm.parametermodel.Group(name='Group A')
    parameters.append_child(group)

    parameter_aa = epcpm.parametermodel.Parameter(name='Parameter AA')
    group.append_child(parameter_aa)
    parameter_ab = epcpm.parametermodel.Parameter(name='Parameter AB')
    group.append_child(parameter_ab)

    parameter_a = epcpm.parametermodel.Parameter(name='Parameter A')
    parameters.append_child(parameter_a)

    symbol_root = epcpm.symbolmodel.Root()

    multiplexed_message = epcpm.symbolmodel.MultiplexedMessage()
    symbol_root.append_child(multiplexed_message)

    multiplexer_a = epcpm.symbolmodel.Multiplexer(name='Multiplexer A')
    multiplexed_message.append_child(multiplexer_a)

    signal_aa = epcpm.symbolmodel.Signal(
        name='Signal PAA',
        parameter_uuid=parameter_aa.uuid,
    )
    multiplexer_a.append_child(signal_aa)

    multiplexer_b = epcpm.symbolmodel.Multiplexer(name='Multiplexer B')
    multiplexed_message.append_child(multiplexer_b)

    signal_ab = epcpm.symbolmodel.Signal(
        name='Signal PAB',
        parameter_uuid=parameter_ab.uuid,
    )
    multiplexer_b.append_child(signal_ab)

    signal_a = epcpm.symbolmodel.Signal(
        name='Signal PA',
        parameter_uuid=parameter_a.uuid,
    )
    multiplexer_b.append_child(signal_a)

    expected = {
        'children': [
            {
                'name': 'Group A',
                'children': [
                    [
                        'MultiplexerA',
                        'SignalPAA',
                    ],
                    [
                        'MultiplexerB',
                        'SignalPAB',
                    ],
                ]
            },
            [
                'MultiplexerB',
                'SignalPA',
            ],
        ]
    }

    builder = epcpm.parameterstohierarchy.builders.wrap(
        wrapped=parameter_root,
        symbol_root=symbol_root,
    )

    assert builder.gen(json_output=False) == expected
