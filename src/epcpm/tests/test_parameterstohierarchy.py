import epyqlib.pm.parametermodel

import epcpm.parameterstohierarchy
import epcpm.canmodel


def test_():
    parameter_root = epyqlib.pm.parametermodel.Root()

    parameters = epyqlib.pm.parametermodel.Group(
        name='Parameters',
        uuid='b95feb06-1f19-4557-8335-4a2287222c69',
    )
    parameter_root.append_child(parameters)

    group = epyqlib.pm.parametermodel.Group(
        name='Group A',
        uuid='c202c286-4eef-4baa-b088-4195c200d944',
    )
    parameters.append_child(group)

    parameter_aa = epyqlib.pm.parametermodel.Parameter(
        name='Parameter AA',
        uuid='b9c38efa-1f2f-458f-980d-bce82ea082fe',
    )
    group.append_child(parameter_aa)
    parameter_ab = epyqlib.pm.parametermodel.Parameter(
        name='Parameter AB',
        uuid='c9d12fb7-e282-4170-bf5d-c880145c2fc5',
    )
    group.append_child(parameter_ab)

    parameter_a = epyqlib.pm.parametermodel.Parameter(
        name='Parameter A',
        uuid='253233ea-3b00-47ec-9b91-623bb5c3dca4',
    )
    parameters.append_child(parameter_a)

    can_root = epcpm.canmodel.Root()

    multiplexed_message = epcpm.canmodel.MultiplexedMessage(
        name='ParameterQuery',
        uuid='3bb49d82-e7fb-4cc1-af8d-f8701fe8b371',
    )
    can_root.append_child(multiplexed_message)

    multiplexer_a = epcpm.canmodel.Multiplexer(
        name='Multiplexer_A',
        uuid='78ce435e-1ba8-424f-aec4-212bbba0c612',
    )
    multiplexed_message.append_child(multiplexer_a)

    signal_aa = epcpm.canmodel.Signal(
        name='Signal_PAA',
        parameter_uuid=parameter_aa.uuid,
        uuid='3c25a151-2ae0-4a8d-bc77-704123aa6547',
    )
    multiplexer_a.append_child(signal_aa)

    multiplexer_b = epcpm.canmodel.Multiplexer(
        name='Multiplexer_B',
        uuid='464d14d3-9bd6-45af-aac8-29cb87faff23',
    )
    multiplexed_message.append_child(multiplexer_b)

    signal_ab = epcpm.canmodel.Signal(
        name='Signal_PAB',
        parameter_uuid=parameter_ab.uuid,
        uuid='84d3eb7a-212c-4634-b46f-92e51b6147fd',
    )
    multiplexer_b.append_child(signal_ab)

    signal_a = epcpm.canmodel.Signal(
        name='Signal_PA',
        parameter_uuid=parameter_a.uuid,
        uuid='db7a51b2-db17-427e-9acc-45d6a988d3d4',
    )
    multiplexer_b.append_child(signal_a)

    expected = {
        'children': [
            {
                'name': 'Group A',
                'children': [
                    [
                        'Multiplexer_A',
                        'Signal_PAA',
                    ],
                    [
                        'Multiplexer_B',
                        'Signal_PAB',
                    ],
                ]
            },
            [
                'Multiplexer_B',
                'Signal_PA',
            ],
        ]
    }

    builder = epcpm.parameterstohierarchy.builders.wrap(
        wrapped=parameter_root,
        can_root=can_root,
    )

    assert builder.gen(json_output=False) == expected
