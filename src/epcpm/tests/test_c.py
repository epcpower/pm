import textwrap

import epcpm.c


def test_format_nested_lists():
    example = [
        'void getSUNSPEC_MODEL17_Nam(void) {',
        [
            'size_t i;',
            'UartName name = modbusHandlerGetName()',
            '',
            'for (i = 0; i < LENGTHOF(name.s); i++) {',
            [
                'sunspecInterface.model17.Nam[i] = name.s[i];',
            ],
            '}',
        ],
        '}',
    ]

    result = epcpm.c.format_nested_lists(it=example)

    assert result == textwrap.dedent('''\
    void getSUNSPEC_MODEL17_Nam(void) {
        size_t i;
        UartName name = modbusHandlerGetName()

        for (i = 0; i < LENGTHOF(name.s); i++) {
            sunspecInterface.model17.Nam[i] = name.s[i];
        }
    }
    ''')
