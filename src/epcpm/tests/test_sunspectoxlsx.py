import csv
import pathlib

import epcpm.project
import epcpm.smdxtosunspec
import epcpm.sunspectoxlsx


this = pathlib.Path(__file__).resolve()
here = this.parent


smdx_path = here/'sunspec'


getset = {
    (1, 'DA', 'get'): r'''sunspecInterface.model1.DA = modbusHandlerGetSlaveAddress();''',
    (1, 'DA', 'set'): r'''modbusHandlerSetSlaveAddress(sunspecInterface.model1.DA);''',
    (17, 'Nam', 'get'): r'''size_t i;
UartName name = modbusHandlerGetName();

for(i=0; i<LENGTHOF(name.s); i++)
{
    sunspecInterface.model17.Nam[i] = name.s[i];
}''',
    (17, 'Nam', 'set'): r'''size_t i;
UartName name;

for(i=0; i<LENGTHOF(name.s); i++)
{
    name.s[i] = sunspecInterface.model17.Nam[i];
}

modbusHandlerSetName(name);''',
    (17, 'Rte', 'get'): r'''uint32_t bps = uartGetBpsFromEnumeration(modbusHandlerGetBaudRate());
sunspecUint32ToSSU32(&sunspecInterface.model17.Rte, bps);''',
    (17, 'Rte', 'set'): r'''int32_t bps = (int32_t)sunspecSSU32ToUint32(&sunspecInterface.model17.Rte);
modbusHandlerSetBaudRate(uartGetBaudEnumeration(bps));''',
    (17, 'Bits', 'get'): r'''UartProtocol protocol = modbusHandlerGetProtocol();

if(protocol == UART_RTU_N82) sunspecInterface.model17.Bits = 2;
else                         sunspecInterface.model17.Bits = 1;''',
    (17, 'Pty', 'get'): r'''UartProtocol protocol = modbusHandlerGetProtocol();

if(protocol == UART_RTU_E81)      sunspecInterface.model17.Pty = SUNSPECMODEL17_PTY_EVEN;
else if(protocol == UART_RTU_O81) sunspecInterface.model17.Pty = SUNSPECMODEL17_PTY_ODD;
else                              sunspecInterface.model17.Pty = SUNSPECMODEL17_PTY_NONE;''',
    (103, 'A', 'get'): r'''sunspecInterface.model103.A         = (int16_t) myround(PCC_getAcMonitorGridCurrentRms_SI(0U, PCC_ACM_APPARENT));''',
    (103, 'AphA', 'get'): r'''sunspecInterface.model103.AphA      = (uint16_t)myround(PCC_getAcMonitorGridCurrentRms_SI(1U, PCC_ACM_APPARENT));''',
    (103, 'AphB', 'get'): r'''sunspecInterface.model103.AphB      = (uint16_t)myround(PCC_getAcMonitorGridCurrentRms_SI(2U, PCC_ACM_APPARENT));''',
    (103, 'AphC', 'get'): r'''sunspecInterface.model103.AphC      = (uint16_t)myround(PCC_getAcMonitorGridCurrentRms_SI(3U, PCC_ACM_APPARENT));''',
    (103, 'PPVphAB', 'get'): r'''sunspecInterface.model103.PPVphAB   = (uint16_t)myround(PCC_getAcMonitorGridVoltageRms_SI(1U, CMM_AC_NETWORK_LOCAL, PCC_ACM_APPARENT, PCC_ACM_LINE) * 10.0f);''',
    (103, 'PPVphBC', 'get'): r'''sunspecInterface.model103.PPVphBC   = (uint16_t)myround(PCC_getAcMonitorGridVoltageRms_SI(2U, CMM_AC_NETWORK_LOCAL, PCC_ACM_APPARENT, PCC_ACM_LINE) * 10.0f);''',
    (103, 'PPVphCA', 'get'): r'''sunspecInterface.model103.PPVphCA   = (uint16_t)myround(PCC_getAcMonitorGridVoltageRms_SI(3U, CMM_AC_NETWORK_LOCAL, PCC_ACM_APPARENT, PCC_ACM_LINE) * 10.0f);''',
    (103, 'PhVphA', 'get'): r'''sunspecInterface.model103.PhVphA    = (uint16_t)myround(PCC_getAcMonitorGridVoltageRms_SI(1U, CMM_AC_NETWORK_LOCAL, PCC_ACM_APPARENT, PCC_ACM_PHASE) * 10.0f);''',
    (103, 'PhVphB', 'get'): r'''sunspecInterface.model103.PhVphB    = (uint16_t)myround(PCC_getAcMonitorGridVoltageRms_SI(2U, CMM_AC_NETWORK_LOCAL, PCC_ACM_APPARENT, PCC_ACM_PHASE) * 10.0f);''',
    (103, 'PhVphC', 'get'): r'''sunspecInterface.model103.PhVphC    = (uint16_t)myround(PCC_getAcMonitorGridVoltageRms_SI(3U, CMM_AC_NETWORK_LOCAL, PCC_ACM_APPARENT, PCC_ACM_PHASE) * 10.0f);''',
    (103, 'W', 'get'): r'''sunspecInterface.model103.W         = (int16_t) myround(sunspecScale(PCC_getAcMonitorGridPowerRms_SI(0U, PCC_ACM_REAL), sunspecInterface.model103.W_SF));''',
    (103, 'Hz', 'get'): r'''sunspecInterface.model103.Hz        = (uint16_t)myround(PCC_getAcMonitorFrequencyHz_SI(0U, CMM_AC_NETWORK_LOCAL) * 10.0f); /// \todo copied from canInterface.c''',
    (103, 'VA', 'get'): r'''sunspecInterface.model103.VA        = (int16_t) myround(sunspecScale(PCC_getAcMonitorGridPowerRms_SI(0U, PCC_ACM_APPARENT), sunspecInterface.model103.VA_SF));''',
    (103, 'VAr', 'get'): r'''sunspecInterface.model103.VAr       = (int16_t) myround(sunspecScale(PCC_getAcMonitorGridPowerRms_SI(0U, PCC_ACM_REACTIVE), sunspecInterface.model103.VAr_SF));''',
    (103, 'PF', 'get'): r'''sunspecInterface.model103.PF        = (int16_t) myround(sunspecScale(PCC_getAcMonitorGridCosPhi_SI(0U), sunspecInterface.model103.PF_SF));''',
    (103, 'DCA', 'get'): r'''sunspecInterface.model103.DCA       = (uint16_t)myround(PCC_getDcMonitorDcCurrent_SI());''',
    (103, 'DCV', 'get'): r'''sunspecInterface.model103.DCV       = (uint16_t)myround(PCC_getDcMonitorDcVoltage_SI());''',
    (103, 'DCW', 'get'): r'''//sunspecInterface.model103.DCW = (int16_t)myround(sunspecScale(myround(_IQtoF(PDC_filt.Out)*PU_DCPOWER), sunspecInterface.model103.DCW_SF));''',
    (103, 'TmpCab', 'get'): r'''sunspecInterface.model103.TmpCab = (int16_t)myround(_IQ22toF(MESD_Measurements.aux.temp.meas.tInternal)*10.0f);''',
    (103, 'TmpSnk', 'get'): r'''sunspecInterface.model103.TmpSnk = (int16_t)myround(_IQ22toF(MESD_Measurements.aux.temp.comp.tInverter)*10.0f); /// \todo CAMPed from canInterface''',
    (103, 'StVnd', 'get'): r'''sunspecInterface.model103.StVnd = (SunspecModel103_StVnd)getStateNumber();''',
    (103, 'Evt1', 'get'): r'''sunspecInterface.model103.Evt1.DC_OVER_VOLT = faultStat.flags.DCOvervoltage;
sunspecInterface.model103.Evt1.MANUAL_SHUTDOWN = faultStat.flags.EStopShutdown;
sunspecInterface.model103.Evt1.OVER_TEMP = faultStat.flags.IGBTOvertemp;
sunspecInterface.model103.Evt1.MEMORY_LOSS = faultStat.flags.InvalidEEHeader || faultStat.flags.InvalidEESection ||
        faultStat.flags.SchedulerBGTask || faultStat.flags.StackOverflow;
sunspecInterface.model103.Evt1.HW_TEST_FAILURE = faultStat.flags.ControlHardwareFail;''',
    (103, 'EvtVnd1', 'get'): r'''sunspecInterface.model103.EvtVnd1.HARDWARE_ENABLE = supervisorGetHardwareEnable();
sunspecInterface.model103.EvtVnd1.AC_PWR_AVAIL = gridMonitor_isNetworkUsable(CMM_AC_NETWORK_LOCAL);
sunspecInterface.model103.EvtVnd1.DC_PWR_AVAIL = !faultStat.flags.DCUndervoltage;
sunspecInterface.model103.EvtVnd1.PWR_CRCT_EN = (PWMD_getControlGroupGenState(CMM_CONTROL_GROUP_CNT, 0U) == PWMD_GENERATION_ACTIVE);
sunspecInterface.model103.EvtVnd1.MX1 = relayIsClosed(relayMX1);
sunspecInterface.model103.EvtVnd1.MX2 = relayIsClosed(relayMX2);
sunspecInterface.model103.EvtVnd1.K1 = relayIsClosed(relayK1);
sunspecInterface.model103.EvtVnd1.K2 = relayIsClosed(relayK2);
sunspecInterface.model103.EvtVnd1.CTL_MSG_VALID = systemGetMasterAlive();
sunspecInterface.model103.EvtVnd1.PWR_CMD_VALID = referenceHandler_getPwrCmdValid();
sunspecInterface.model103.EvtVnd1.CUR_CMD_VALID = referenceHandler_getCurCmdValid();
sunspecInterface.model103.EvtVnd1.DC_CMD_VALID = referenceHandler_getDcCmdValid();
sunspecInterface.model103.EvtVnd1.PH_ROTAT_STAT     = (PCD_getPhaseSequenceDetect(CMM_AC_NETWORK_LOCAL) == PCD_PHASE_SEQUENCE_POSITIVE);
sunspecInterface.model103.EvtVnd1.LV_DETECTED = gridMonitor_isNetworkLive(CMM_AC_NETWORK_LOCAL);
sunspecInterface.model103.EvtVnd1.REM_AC_AVAIL = false;
sunspecInterface.model103.EvtVnd1.REM_PH_ROTAT_STAT = false;
sunspecInterface.model103.EvtVnd1.REM_LV_DETECTED = false;

sunspecInterface.model103.EvtVnd1.DI1_STAT = digitalInputRead(&digins[0]);
sunspecInterface.model103.EvtVnd1.DI2_STAT = digitalInputRead(&digins[1]);
sunspecInterface.model103.EvtVnd1.DI3_STAT = digitalInputRead(&digins[2]);
sunspecInterface.model103.EvtVnd1.DI4_STAT = digitalInputRead(&digins[3]);

sunspecInterface.model103.EvtVnd1.DO1_STAT = digitalOutputRead(&digouts[0]);
sunspecInterface.model103.EvtVnd1.DO2_STAT = digitalOutputRead(&digouts[1]);
sunspecInterface.model103.EvtVnd1.DO3_STAT = digitalOutputRead(&digouts[2]);
sunspecInterface.model103.EvtVnd1.DO4_STAT = digitalOutputRead(&digouts[3]);''',
    (65534, 'CmdBits', 'set'): r'''bool forceRelayCmds[relayListLength];

systemClearFaults(sunspecInterface.model65534.CmdBits.FltClr);

if (sunspecInterface.model65534.CmdBits.FltClr) {
    resetPumpFaults(&pumpDrive);
}

if (sunspecInterface.model65534.CmdBits.WrnClr) {
    WARNING_CLEARALL();
}

//SyncToRemote = sunspecInterface.model65534.CmdBits.RemoteSync;
fanSetSpeedOverride(&fanCoolant, sunspecInterface.model65534.CmdBits.ForceFan, 100);
supervisorSetHwEnableLogic(sunspecInterface.model65534.CmdBits.InvertHwEnable);
afeParams->cfgFlags.enableUPSMode = sunspecInterface.model65534.CmdBits.EnableUps;

if (sunspecInterface.model65534.CmdBits.EnableSplitPhase == 1) {
    PCD_setPresetDisplacementRequest(PCD_PHASE_DISPLACEMENT_180);
} else {
    PCD_setPresetDisplacementRequest(PCD_PHASE_DISPLACEMENT_120);
}

if (sunspecInterface.model65534.CmdBits.PhaseRotation == 1) {
    PCD_setPhaseSequenceRequest(PCD_PHASE_SEQUENCE_POSITIVE);
} else {
    PCD_setPhaseSequenceRequest(PCD_PHASE_SEQUENCE_NEGATIVE);
}

forceRelayCmds[relayMX1] = sunspecInterface.model65534.CmdBits.ForceMX1;
forceRelayCmds[relayMX2] = sunspecInterface.model65534.CmdBits.ForceMX2;
forceRelayCmds[relayK1]  = sunspecInterface.model65534.CmdBits.ForceK1 ;
forceRelayCmds[relayK2]  = sunspecInterface.model65534.CmdBits.ForceK2 ;

afeHandleRelayCmds(&forceRelayCmds);''',
    (65534, 'CmdRealPwr', 'set'): r'''if(systemIsModbusControlActive() && pqCommandsValid()) {     referenceHandler_setP(sunspecSSS32ToInt32(&sunspecInterface.model65534.CmdRealPwr)*0.01f); } ''',
    (65534, 'CmdReactivePwr', 'set'): r'''if(systemIsModbusControlActive() && pqCommandsValid()) {
    referenceHandler_setQ(sunspecSSS32ToInt32(&sunspecInterface.model65534.CmdReactivePwr)*0.01f);
}
''',
    (65534, 'CmdV', 'set'): r'''referenceHandler_setVCmd(sunspecInterface.model65534.CmdV*0.1f);''',
    (65534, 'CmdHz', 'set'): r'''(void)PPC_setCommonConfigNominalFrequency((float)sunspecInterface.model65534.CmdHz * 0.1f);''',
    (65534, 'CtlSrc', 'get'): r'''if (systemIsModbusControlActive()) {
     sunspecInterface.model65534.CtlSrc = SUNSPECMODEL65534_CTLSRC_Modbus;    
} else {
     sunspecInterface.model65534.CtlSrc = SUNSPECMODEL65534_CTLSRC_CAN;     
}''',
    (65534, 'CtlSrc', 'set'): r'''if (sunspecInterface.model65534.CtlSrc == SUNSPECMODEL65534_CTLSRC_Modbus) {         
    systemSetModbusControlActive();     
} else {
    systemSetCanControlActive();     
}''',
    (65534, 'IMPPT', 'get'): r'''#ifdef HYDRA
	sunspecInterface.model65534.IMPPT   = (int16_t)myround(_IQtoF(DCDC_getControlSourceTotalCurrentRef(DCDC_CTRL_SRC_MPPT, true)) * PU_Iline);
#endif''',
    (65534, 'Ivctl', 'get'): r'''#ifdef HYDRA
	sunspecInterface.model65534.Ivctl   = (int16_t)myround(_IQtoF(DCDC_getControlSourceTotalCurrentRef(DCDC_CTRL_SRC_VOLTAGE, true)) * PU_Iline);
#endif''',
    (65534, 'Vsol', 'get'): r'''#ifdef HYDRA
	sunspecInterface.model65534.Vsol    = (int16_t)myround(_IQtoF(-remoteLineVoltages[LV_FBK_SOL]) * PU_Vline_Rem);
#endif''',
    (65534, 'Vbat', 'get'): r'''#ifdef HYDRA
	sunspecInterface.model65534.Vbat    = (int16_t)myround(_IQtoF( remoteLineVoltages[LV_FBK_BAT]) * PU_Vline_Rem);
#endif''',
    (65534, 'Spcl', 'set'): r'''static bool writingEE = false;

if((sunspecInterface.model65534.Spcl.Save)&&(!writingEE)) {
    writingEE = true;   
    eeHandlerSave(false); //store to NV  
} else {   
    if(!sunspecInterface.model65534.Spcl.Save) {       
    writingEE = false;   
    }  
}''',
    (65534, 'SysFlt', 'get'): r'''sunspecInterface.model65534.SysFlt  = faultStat.flags.ControlHardwareFail;
sunspecInterface.model65534.SysFlt += faultStat.flags.SchedulerBGTask   << 1;
sunspecInterface.model65534.SysFlt += faultStat.flags.EEUninitialized   << 2;
sunspecInterface.model65534.SysFlt += faultStat.flags.StackOverflow     << 3;
sunspecInterface.model65534.SysFlt += faultStat.flags.InsufficientHeap  << 4;
sunspecInterface.model65534.SysFlt += faultStat.flags.PWMISROverrun     << 5;
sunspecInterface.model65534.SysFlt += faultStat.flags.SchedulerTaskInit << 6;
sunspecInterface.model65534.SysFlt += faultStat.flags.msISROverrun << 7;
sunspecInterface.model65534.SysFlt += faultStat.flags.tenMsISROverrun << 8;''',
    (65534, 'FltFlgs', 'get'): r'''sunspecInterface.model65534.FltFlgs.Estp    = faultStat.flags.EStopShutdown;
sunspecInterface.model65534.FltFlgs.ACOC    = faultStat.flags.ACOvercurrent;
sunspecInterface.model65534.FltFlgs.DCOC    = faultStat.flags.DCOvercurrent;
sunspecInterface.model65534.FltFlgs.DCOV    = faultStat.flags.DCOvervoltage;
sunspecInterface.model65534.FltFlgs.PDOT    = faultStat.flags.IGBTOvertemp;
sunspecInterface.model65534.FltFlgs.IOT     = faultStat.flags.InverterOvertemp;
sunspecInterface.model65534.FltFlgs.CmdMsg  = faultStat.flags.LossOfValidCmd;
sunspecInterface.model65534.FltFlgs.DCUV    = faultStat.flags.DCUndervoltage;
sunspecInterface.model65534.FltFlgs.GrdLss  = faultStat.flags.LossOfAC;
sunspecInterface.model65534.FltFlgs.Trans   = faultStat.flags.IllegalTransition;
sunspecInterface.model65534.FltFlgs.EEH     = faultStat.flags.InvalidEEHeader;
sunspecInterface.model65534.FltFlgs.EES     = faultStat.flags.InvalidEESection;
sunspecInterface.model65534.FltFlgs.Cool    = faultStat.flags.CoolingSystemFail;
sunspecInterface.model65534.FltFlgs.TOLAC   = faultStat.flags.TimedACOverload;
sunspecInterface.model65534.FltFlgs.TOLDC   = faultStat.flags.TimedDCOverload;
sunspecInterface.model65534.FltFlgs.SIO     = faultStat.flags.SIOTimeout;
sunspecInterface.model65534.FltFlgs.CtlBd   = faultStat.flags.CtlBdVoltage;
sunspecInterface.model65534.FltFlgs.Iimblnc = faultStat.flags.IlegImbalance;
sunspecInterface.model65534.FltFlgs.DiDt    = faultStat.flags.Didt;
sunspecInterface.model65534.FltFlgs.Flw     = faultStat.flags.LowCoolingFlow;
sunspecInterface.model65534.FltFlgs.POR     = faultStat.flags.PORTimeout;
sunspecInterface.model65534.FltFlgs.Thrm    = faultHandlerIsCfgdFaultActive(FLT_CFG_THERMAL_OVERLOAD);
sunspecInterface.model65534.FltFlgs.Fan     = faultHandlerIsCfgdFaultActive(FLT_CFG_FAN_CIRCUIT);''',
    (65534, 'WrnFlgs', 'get'): r'''sunspecInterface.model65534.WrnFlgs.CANW    = warningStat.flags.CANWarning;
sunspecInterface.model65534.WrnFlgs.CANEP   = warningStat.flags.CANErrorPassive;
sunspecInterface.model65534.WrnFlgs.Thrm    = faultHandlerIsCfgdWarningActive(FLT_CFG_THERMAL_OVERLOAD);
sunspecInterface.model65534.WrnFlgs.Fan     = faultHandlerIsCfgdWarningActive(FLT_CFG_FAN_CIRCUIT);''',
    (65534, 'CmdRealCurrent', 'set'): r'''if(systemIsModbusControlActive()) {
    referenceHandler_setId(sunspecInterface.model65534.CmdRealCurrent);
}''',
    (65534, 'CmdReactiveCurrent', 'set'): r'''if(systemIsModbusControlActive()) {
    referenceHandler_setIq(sunspecInterface.model65534.CmdReactiveCurrent);
}
''',
    (65534, 'RealCurrent', 'get'): r'''sunspecInterface.model65534.RealCurrent     = (int16_t)myround(PCC_getAcMonitorGridCurrentRms_SI(0U, PCC_ACM_REAL));''',
    (65534, 'ReactiveCurrent', 'get'): r'''sunspecInterface.model65534.ReactiveCurrent = (int16_t)myround(PCC_getAcMonitorGridCurrentRms_SI(0U, PCC_ACM_REACTIVE));''',
    (65534, 'LocVAC', 'get'): r'''sunspecInterface.model65534.LocVAC          = (int16_t)myround(PCC_getAcMonitorGridVoltageRms_SI(0U, CMM_AC_NETWORK_LOCAL, PCC_ACM_APPARENT, PCC_ACM_LINE) * 10.0f);''',
    (65534, 'RemPhVphA', 'get'): r'''//RemPhVphA  = (uint16_t)myround(_IQtoF(ieee1547_getLineToNeutralVoltage(&ieee1547LVM, IEEE1547_VLINEA))* PU_VlineRMS * 10.0f);''',
    (65534, 'RemPhVphB', 'get'): r'''//RemPhVphB  = (uint16_t)myround(_IQtoF(ieee1547_getLineToNeutralVoltage(&ieee1547LVM, IEEE1547_VLINEB))* PU_VlineRMS * 10.0f);''',
    (65534, 'RemPhVphC', 'get'): r'''//RemPhVphC  = (uint16_t)myround(_IQtoF(ieee1547_getLineToNeutralVoltage(&ieee1547LVM, IEEE1547_VLINEC))* PU_VineRMS * 10.0f);''',
    (65534, 'RemVAC', 'get'): r'''//sunspecInterface.model65534.RemVAC = (int16_t)myround(_IQtoF(vAcRemote_filt.Out)*PU_Vline*10.0f);''',
    (65534, 'RemHz', 'get'): r'''//sunspecInterface.model65534.RemHz = (int16_t)myround(pll_getFrequency(&pll_remote)*10.0f);''',
    (65534, 'TmpInt', 'get'): r'''sunspecInterface.model65534.TmpInt = (int16_t)myround(_IQ22toF(MESD_Measurements.aux.temp.meas.tInternal)*10.0f);''',
    (65534, 'TmpInlet', 'get'): r'''#ifdef AIRCOOLED_HEATSINK
	sunspecInterface.model65534.TmpInlet = (int16_t)myround(_IQ22toF(MESD_Measurements.aux.temp.comp.tInv)*10.0f); //max IGBT temp
#else
	sunspecInterface.model65534.TmpInlet = (int16_t)myround(_IQ22toF(MESD_Measurements.aux.temp.meas.tInlet)*10.0f);
#endif''',
    (65534, 'RemPPVphCA', 'get'): r'''//RemPPVphCA = (uint16_t)myround(_IQtoF(ieee1547_getLineToLineVoltage   (&ieee1547LVM, IEEE1547_VLINEA))* PU_VlineRMS * 10.0f);''',
    (65534, 'RemPPVphAB', 'get'): r'''//RemPPVphAB = (uint16_t)myround(_IQtoF(ieee1547_getLineToLineVoltage   (&ieee1547LVM, IEEE1547_VLINEB))* PU_VlineRMS * 10.0f);''',
    (65534, 'RemPPVphBC', 'get'): r'''//RemPPVphBC = (uint16_t)myround(_IQtoF(ieee1547_getLineToLineVoltage   (&ieee1547LVM, IEEE1547_VLINEC))* PU_VlineRMS * 10.0f);''',
    (65534, 'DcILim', 'set'): r'''if(systemIsModbusControlActive()) {
    referenceHandler_setIdcLim(sunspecInterface.model65534.DcILim);
}''',
    (65534, 'DcVLim', 'set'): r'''if(systemIsModbusControlActive()) {
    referenceHandler_setVdcLim(sunspecInterface.model65534.DcVLim*0.1f);
}''',
    (65534, 'LineILim', 'set'): r'''if(systemIsModbusControlActive()) {
    referenceHandler_setIlineLim(sunspecInterface.model65534.LineILim);
}''',
    (65534, 'InputCurrent', 'set'): r'''if(systemIsModbusControlActive()) {
    referenceHandler_setInputCurrent(sunspecInterface.model65534.InputCurrent);
}''',
}


def test_x():
    project = epcpm.project.loadp(here/'project'/'project.pmp')

    attrs_model = project.models.sunspec
    parameter_model = project.models.parameters

    enumerations = parameter_model.list_selection_roots['enumerations']
    sunspec_types = epcpm.sunspecmodel.build_sunspec_types_enumeration()
    enumerations.append_child(sunspec_types)
    parameter_model.list_selection_roots['sunspec types'] = sunspec_types

    requested_models = [1, 17, 103, 65534]
    sunspec_models = epcpm.smdxtosunspec.import_models(
        *requested_models,
        parameter_model=parameter_model,
        paths=[smdx_path],
    )

    for sunspec_model in sunspec_models:
        attrs_model.root.append_child(sunspec_model)

    points = (
        (model, block, point)
        for model in attrs_model.root.children
        for block in model.children
        for point in block.children
    )

    for model, block, point in points:
        parameter = attrs_model.node_from_uuid(point.parameter_uuid)
        for direction in ('get', 'set'):
            key = (model.id, parameter.abbreviation, direction)
            accessor = getset.get(key)
            if accessor is not None:
                setattr(point, direction, accessor)

    project.filename = here/'project_with_sunspec'/'project.pmp'
    project.paths['sunspec'] = 'sunspec.json'
    project.save()

    builder = epcpm.sunspectoxlsx.builders.wrap(
        wrapped=attrs_model.root,
        parameter_uuid_finder=attrs_model.node_from_uuid,
        parameter_model=project.models.parameters,
    )

    workbook = builder.gen()

    assert workbook.sheetnames == [
        'License Agreement',
        'Summary',
        'Index',
        '1',
        '17',
        '103',
        '65534',
    ]

    workbook.save('test_sunspectoxlsx.xlsx')

    with open('test_sunspectoxlsx.csv', 'w', newline='') as file:
        writer = csv.writer(file)

        for sheet in workbook.worksheets:
            for row in sheet.rows:
                writer.writerow(cell.value for cell in row)
