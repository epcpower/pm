import itertools
import os
import pathlib
import re

import canmatrix
import click.testing

import epyqlib.tests.common

import epcpm.cli.importsym
import epcpm.cli.exportsym


round_trip = pathlib.Path(__file__).parents[3] / 'roundtrip'
project = round_trip / 'project.pmp'
example_device = epyqlib.tests.common.new_devices()[('develop', 'factory')]
exported_can = (
        round_trip / 'exported'
).with_suffix(example_device.can.suffix)
exported_hierarchy = (
        round_trip / 'hierarchy.parameters.json'
).with_suffix(example_device.hierarchy.suffix)


def test_import():
    runner = click.testing.CliRunner()

    result = runner.invoke(
        epcpm.cli.importsym.cli,
        [
            '--sym', example_device.can,
            '--hierarchy', example_device.hierarchy,
            '--project', project,
            '--can', round_trip / 'can.json',
            '--parameters', round_trip / 'parameters.json',
        ],
        catch_exceptions=False,
    )
    print(result.output)

    assert result.exit_code == 0


def test_export():
    runner = click.testing.CliRunner()

    result = runner.invoke(
        epcpm.cli.exportsym.cli,
        [
            '--project', project,
            '--sym', exported_can,
            '--hierarchy', exported_hierarchy,
        ],
        catch_exceptions=False,
    )
    print(result.output)

    assert result.exit_code == 0


def assert_signals_equal(
        original,
        original_frame,
        exported,
        exported_frame,
):
    assert_attributes_equal(
        original=original,
        exported=exported,
        attributes=(
            'enumeration',
            'is_float',
            'is_little_endian',
            'is_multiplexer',
            'is_signed',
            'max',
            'min',
            'multiplex',
            'factor',
            'offset',
            'signalsize',
            'startbit',
            'unit',
        ),
    )

    if 'LongName' in original.attributes:
        assert original.attributes == exported.attributes
    else:
        tweaked = dict(exported.attributes)
        tweaked.pop('LongName', None)
        assert original.attributes == tweaked

    factory = '<factory>'

    def split_and_access_level(comment):

        split = comment.split()

        return (
            factory if factory in split else None,
            [x for x in split if x != factory],
        )

    original_factory, original_comment = split_and_access_level(
        original.comment,
    )
    exported_factory, exported_comment = split_and_access_level(
        exported.comment,
    )

    assert original_comment == exported_comment

    not_applicable = (
        'readparam_command',
        'readparam_status',
        'meta',
    )
    if original.name.casefold() not in not_applicable:
        original_mux = [
            x for x in original_frame.signals if x.multiplex == 'Multiplexor'
        ]
        original_mux, = original_mux if original_mux else (None,)

        exported_mux = [
            x for x in exported_frame.signals if x.multiplex == 'Multiplexor'
        ]
        exported_mux, = exported_mux if exported_mux else (None,)

        if original_mux is None:
            assert original_mux == exported_mux

        original_access_level = original_factory == factory
        if original_mux is not None:
            original_access_level = (
                    original_access_level
                    or (
                            original is not original_mux
                            and factory in original_mux.comments[
                                original.multiplex]
                    )
            )
        else:
            original_access_level = (
                    original_access_level
                    or factory in original_frame.comment
            )

        exported_access_level = exported_factory == factory
        if exported_mux is not None:
            exported_access_level = (
                    exported_access_level
                    or (
                            exported is not exported_mux
                            and factory in exported_mux.comments[
                                exported.multiplex]
                    )
            )
        else:
            exported_access_level = (
                    exported_access_level
                    or factory in exported_frame.comment
            )

        access_level_matches = original_access_level == exported_access_level

        assert access_level_matches

    assert_varied_dict_equal(original.values, exported.values)

    _, original_comments = split_and_access_level(original.comment)
    _, exported_comments = split_and_access_level(exported.comment)

    assert original_comments == exported_comments


def get_name(x):
    return x.name


def sorted_names(names):
    return sorted(names, key=lambda x: (x.casefold(), x))


def unvary_signal_names(name):
    changes = (
        (r'(IGBT|Diode)_R(\d)', r'\1_r\2'),
        (r'(IGBT|Diode)_Tc(\d)', r'\1_tc\2'),
        ('Rii', 'rii'),
        ('Rdi', 'rdi'),
        ('Alpha', 'alpha'),
        ('Amps', 'amps'),
        ('Beta', 'beta'),
        (r'Leg(\d)', r'leg\1'),
        ('CurrentLCL', 'currentLCL'),
        ('MinPulseTime', 'minPulseTime'),
        ('N15V_Supply', 'n15V_Supply'),
        (r'V([p\d]+)_Supply', r'v\1_Supply'),
        ('Phase([ABC])', r'phase\1'),
        ('PostTriggerDuration_S', 'PostTriggerDuration_s'),
        (r'LegInductance(\d)', r'legInductance\1'),
        ('TempSetpoint', 'tempSetpoint'),
        ('LineCurrentLimit', 'lineCurrentLimit'),
        ('Dc(Current|Voltage)Limit', r'dc\1Limit'),
        ('Dc(Current|Voltage)Limit_Echo', r'dc\1Limit_echo'),
        ('Line(Current|Voltage)Limit_Echo', r'line\1Limit_echo'),
        ('PpcIslDroop([VF])_IBpt', r'PpcIslDroop\1_iBpt'),
        ('PpcIslDroop([VF])_DBpt', r'PpcIslDroop\1_dBpt'),
        ('PpcIslDroop([VF])_QBpt', r'PpcIslDroop\1_qBpt'),
        ('Ig_Max', 'Ig_max'),
        (
            r'(MesdConfigLutCalibration_)T(Igbt|Aux|Motor)_(\d+)',
            r'\1t\2_\3',
        ),
        (
            '(ProtTemperatureLimitTrip_)T({})_(Running|Stopped)'.format(
                '|'.join((
                    'Inverter',
                    'Internal',
                    'Device',
                    'Inlet',
                    'Delta',
                )),
            ),
            lambda m: f'{m.group(1)}t{m.group(2)}_{m.group(3).casefold()}',
        ),
        (
            '(ProtCtrlVoltageLimitTrip)_V(Pos|Neg)(24|15|5|3)',
            r'\1_v\2\3',
        ),
        (r'(.*)_TxRate', r'\1_txRate'),
        *(
            (x, lambda m: m.group(0)[0].casefold() + m.group(0)[1:])
            for x in (
                'DIg',
                'DpwmStrategy',
                'DcGroup',
                'D[012]',
                'Q([012]|Ig)',
                'AcGroup',
                '(C|G)(L|R)s',
                'AcHalfPeriodTrack',
                'DtCompEnable',
                'DutyLimit',
                'EeSaveInProgress',
                'EntryPulseNr',
                'FCut(F|Ig|V)',
                'FDev(H|L)',
                'FMax',
                'FMin',
                'FNom',
                'FourWireEnable',
                'FSw(Hysteresis|Minimum|Request)',
                'I([012]|Abs|Delta|Dlt)',
                'Ind(IslStart|Threshold)',
                'K(Alpha|Apply|Phi|Vq)',
                'Limit(XY|Z)',
                'Lim(Lower|Upper)',
                'Load(L|PhiTau|R)',
                'Min(Current|VectorTime|Volt)',
                'ModDepthLimit(Beg|End)',
                'NetworkFrequency',
                'P(Delta|PhaseSel)',
                'PhaseSel',
                'PhiAbs',
                'Sat(CompEnable|Voltage)',
                'S(C|R)s',
                'SRv',
                'SimModeEnable',
                'SpectrumAdjustTau',
                'SpreadSpect(Enable|Inject)',
                'StandardDeviation',
                'SyncMod(Enable|Strategy)',
                'Tau',
                'T(Adapt|Deadband|Delta)',
                'Threshold',
                'TimeConst',
                'TrigCalTime',
                'TripTime',
                'TSwitch',
                'U',
                'VDelta',
                'VectAlignCtrl_(K[dp]|StepSat|Ti)',
                'V(Max|Min)',
                'VoltMag',
                'VsComp(Enable|Tau)',
                'Y',
                'ZeroVectorStrategy',
            )
        ),
        *(
            (
                r'(.*)_({x})_(.*)'.format(x=x),
                lambda
                    m: f'{m.group(1)}_{m.group(2).casefold()}_{m.group(3)}',
            )
            for x in (
                'Seconds',
                'Hertz',
                'Percent_Nominal_Volts',
                'Percent_Nominal_Var',
                'Percent_Nominal_Pwr',
                'Percent',
                'Nominal_Volts',
            )
        ),
        *(
            (x, lambda m: m.group(1) + m.group(2) + m.group(3).casefold())
            for x in (
                '(DcCurrent|DcVoltage|ReactivePower|RealPower)()(Limit|_Echo)',
                '(ReadParam|SaveToEE)(_)(Command|Status)',
                '(TempTmodel)(_)(Calculated)',
                '({})(_)(Echo)'.format(
                    '|'.join((
                        'Enable',
                        'FaultClr',
                        'WarningClr',
                        'ReactiveCurrent',
                        'RealCurrent',
                        'IslandReconnect',
                    )),
                ),
                '({})(_)(Measured)'.format(
                    '|'.join((
                        'TempDeviceBrdg[ABC]',
                        'CurrentAC',
                        'Frequency',
                        'VoltageAC',
                        'FrequencyRemote',
                        'VoltageAcRemote',
                        'SolarCurrent',
                        'SolarVoltage',
                        'CurrentDC',
                        'VoltageDCBus',
                        'VoltageDCInput',
                        'L[123]Current',
                        'L[123]ToL[123]Voltage',
                        '.*',
                    )),
                ),
        )
        ),
    )

    tweaked = name
    for pattern, replacement in changes:
        tweaked = re.sub(f'^{pattern}$', replacement, tweaked)

    return tweaked


def assert_signal_list_equal(
        original,
        original_frame,
        exported,
        exported_frame,
):
    original_names = sorted_names(
        x.name
        for x in original
    )
    exported_names = sorted_names(
        unvary_signal_names(x.name)
        for x in exported
    )

    case_insensitive = (
        'controlsvariant',
        'current',
        'didt',
        'dqccterm',
        'freq',
        'gain',
        'level',
        'limit',
        'max',
        'min',
        'r',
        'rate',
        'resistance',
        'tc',
        'temp',
        'temperature',
        'time',
        'volts',
    )

    zipped = itertools.zip_longest(original_names, exported_names)
    for original_name, exported_name in zipped:
        if original_name.casefold() in case_insensitive:
            assert original_name.casefold() == exported_name.casefold()
        else:
            assert original_name == exported_name

    def key(x):
        return (
            x.name.casefold(), x.multiplex
            if x.multiplex is not None
            else float('-inf')
        )

    zipped = itertools.zip_longest(
        sorted(original, key=key),
        sorted(exported, key=key),
    )
    for original_signal, exported_signal in zipped:
        assert_signals_equal(
            original=original_signal,
            original_frame=original_frame,
            exported=exported_signal,
            exported_frame=exported_frame,
        )


def assert_attributes_equal(original, exported, *, attributes):
    for attribute in attributes:
        assert getattr(original, attribute) == getattr(exported, attribute)


def assert_varied_dict_equal(original, exported):
    zipped = itertools.zip_longest(
        sorted(original.items()),
        sorted(exported.items()),
    )
    for (original_value, original_name), (exported_value, exported_name) in zipped:
        assert original_value == exported_value

        tweaked = unvary_signal_names(exported_name)
        assert original_name == tweaked


def assert_frames_equal(original, exported):
    assert_attributes_equal(
        original=original,
        exported=exported,
        attributes=(
            'name',
            'id',
            'extended',
            'attributes',
            'comment',
            'is_multiplexed',
            'size',
        ),
    )

    assert_varied_dict_equal(original.mux_names, exported.mux_names)

    assert_signal_list_equal(
        original=original.signals,
        original_frame=original,
        exported=exported.signals,
        exported_frame=exported,
    )


def collect_attribute(sequence, name):
    return {getattr(x, name) for x in sequence}


def assert_frame_lists_equal(original, exported):
    original_names = collect_attribute(original, 'name')
    exported_names = collect_attribute(exported, 'name')

    assert original_names == exported_names

    zipped = itertools.zip_longest(
        sorted(original, key=get_name),
        sorted(exported, key=get_name),
    )
    for original_frame, exported_frame in zipped:
        assert_frames_equal(original_frame, exported_frame)


def assert_value_tables_equal(original, exported):
    return original == exported


def test_roundtrip():
    original, = canmatrix.formats.loadp(os.fspath(example_device.can)).values()
    exported, = canmatrix.formats.loadp(os.fspath(exported_can)).values()

    assert_frame_lists_equal(original.frames, exported.frames)
    assert_value_tables_equal(original.valueTables, exported.valueTables)

    print()
