:- encoding(utf8).
% ============================================================
% BASE DE HECHOS PURA
% Códigos de falla en minúscula; códigos de repuesto entre comillas simples.
% Severidades permitidas: leve | moderada | urgente
% ============================================================

% sintoma_falla(Sintoma, CodigoFalla)
sintoma_falla(ruido_frenos,        f_frenos_01).
sintoma_falla(pedal_esponjoso,     f_frenos_01).
sintoma_falla(vibracion_volante,   f_frenos_02).
sintoma_falla(vibracion_volante,   f_suspension_01).
sintoma_falla(humo_escape,         f_motor_01).
sintoma_falla(luz_motor_encendida, f_motor_01).
sintoma_falla(ruido_suspension,    f_suspension_01).

% falla_descripcion(CodigoFalla, Descripcion)
falla_descripcion(f_frenos_01,
    'Desgaste severo de pastillas de freno y aire en el sistema hidráulico').
falla_descripcion(f_frenos_02,
    'Discos de freno alabeados que provocan vibración al frenar').
falla_descripcion(f_motor_01,
    'Falla de combustión por bujías desgastadas y sensor de oxígeno defectuoso').
falla_descripcion(f_suspension_01,
    'Desgaste de amortiguadores y bujes de suspensión').

% severidad_falla(CodigoFalla, Nivel)   Nivel: leve | moderada | urgente
severidad_falla(f_frenos_01,     urgente).
severidad_falla(f_frenos_02,     moderada).
severidad_falla(f_motor_01,      moderada).
severidad_falla(f_suspension_01, leve).

% horas_estimadas(CodigoFalla, Horas)
horas_estimadas(f_frenos_01,     2.5).
horas_estimadas(f_frenos_02,     2.0).
horas_estimadas(f_motor_01,      4.0).
horas_estimadas(f_suspension_01, 3.0).

% falla_repuesto(CodigoFalla, CodigoRepuesto, Cantidad)
falla_repuesto(f_frenos_01,     'REP-001', 2).
falla_repuesto(f_frenos_01,     'REP-002', 1).
falla_repuesto(f_frenos_02,     'REP-003', 2).
falla_repuesto(f_frenos_02,     'REP-001', 2).
falla_repuesto(f_motor_01,      'REP-004', 4).
falla_repuesto(f_motor_01,      'REP-005', 1).
falla_repuesto(f_suspension_01, 'REP-006', 2).
falla_repuesto(f_suspension_01, 'REP-007', 2).