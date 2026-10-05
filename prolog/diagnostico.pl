:- encoding(utf8).
:- use_module(library(lists)).
:- use_module(library(apply)).

% ============================================================
% BASE DE HECHOS
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

% falla_info(CodigoFalla, Descripcion, Severidad, HorasManoObra)
falla_info(f_frenos_01,
    'Desgaste severo de pastillas de freno y aire en el sistema hidráulico',
    urgente, 2.5).
falla_info(f_frenos_02,
    'Discos de freno alabeados que provocan vibración al frenar',
    moderada, 2.0).
falla_info(f_motor_01,
    'Falla de combustión por bujías desgastadas y sensor de oxígeno defectuoso',
    moderada, 4.0).
falla_info(f_suspension_01,
    'Desgaste de amortiguadores y bujes de suspensión',
    leve, 3.0).

% falla_repuesto(CodigoFalla, CodigoRepuesto, Cantidad)
falla_repuesto(f_frenos_01,     'REP-001', 2).
falla_repuesto(f_frenos_01,     'REP-002', 1).
falla_repuesto(f_frenos_02,     'REP-003', 2).
falla_repuesto(f_frenos_02,     'REP-001', 2).
falla_repuesto(f_motor_01,      'REP-004', 4).
falla_repuesto(f_motor_01,      'REP-005', 1).
falla_repuesto(f_suspension_01, 'REP-006', 2).
falla_repuesto(f_suspension_01, 'REP-007', 2).

% ============================================================
% INFERENCIA
% ============================================================

% diagnosticar_lista(+Sintomas, -Fallas)
% Fallas únicas, en orden de primera aparición. Síntomas desconocidos se ignoran.
diagnosticar_lista(Sintomas, Fallas) :-
    findall(F, (member(S, Sintomas), sintoma_falla(S, F)), Todas),
    list_to_set(Todas, Fallas).

% es_urgente_recursivo(+Fallas): éxito si al menos una falla es urgente.
es_urgente_recursivo([F|_]) :-
    falla_info(F, _, urgente, _), !.
es_urgente_recursivo([_|Resto]) :-
    es_urgente_recursivo(Resto).

% hay_severidad(+Fallas, +Severidad): éxito si alguna falla tiene esa severidad.
hay_severidad([F|_], Sev) :-
    falla_info(F, _, Sev, _), !.
hay_severidad([_|Resto], Sev) :-
    hay_severidad(Resto, Sev).

% evaluar_criticidad_global(+Fallas, -Criticidad)
% (la unificación con la salida va al final para que funcione también con Criticidad ya instanciada)
evaluar_criticidad_global(Fallas, Criticidad) :-
    (   es_urgente_recursivo(Fallas)     -> C = urgente
    ;   hay_severidad(Fallas, moderada)  -> C = moderada
    ;   C = leve
    ),
    Criticidad = C.

% obtener_repuestos_necesarios(+Fallas, -Repuestos)
% Repuestos = [repuesto(Codigo, Cantidad), ...] sin códigos duplicados (cantidades sumadas).
obtener_repuestos_necesarios(Fallas, Repuestos) :-
    findall(Cod-Cant,
            ( member(F, Fallas), falla_repuesto(F, Cod, Cant) ),
            Pares),
    sumar_repuestos(Pares, Repuestos).

sumar_repuestos([], []).
sumar_repuestos([Cod-Cant|Resto], [repuesto(Cod, Total)|Sumados]) :-
    partition(mismo_codigo(Cod), Resto, Iguales, Otros),
    foldl(acumular_cantidad, Iguales, Cant, Total),
    sumar_repuestos(Otros, Sumados).

mismo_codigo(Cod, Cod-_).
acumular_cantidad(_-C, Acc0, Acc) :- Acc is Acc0 + C.

% calcular_horas_totales(+Fallas, -HorasTotales) recursivo
calcular_horas_totales([], 0.0).
calcular_horas_totales([F|Resto], Total) :-
    falla_info(F, _, _, H),
    calcular_horas_totales(Resto, Parcial),
    Total is H + Parcial.

% ============================================================
% SALIDA PARA EL PUENTE PYTHON (líneas separadas por tabulación)
% ============================================================

emitir_diagnostico(Sintomas) :-
    set_stream(user_output, encoding(utf8)),
    diagnosticar_lista(Sintomas, Fallas),
    forall(member(F, Fallas), emitir_falla(F)),
    evaluar_criticidad_global(Fallas, Crit),
    format("CRITICIDAD\t~w~n", [Crit]),
    calcular_horas_totales(Fallas, Horas),
    format("TOTAL_HORAS\t~w~n", [Horas]),
    obtener_repuestos_necesarios(Fallas, Reps),
    forall(member(repuesto(C, Q), Reps),
           format("TOTAL_REPUESTO\t~w\t~w~n", [C, Q])).

emitir_falla(F) :-
    falla_info(F, Desc, Sev, Horas),
    format("FALLA\t~w\t~w\t~w\t~w~n", [F, Desc, Sev, Horas]),
    forall(falla_repuesto(F, Cod, Cant),
           format("REPUESTO\t~w\t~w\t~w~n", [F, Cod, Cant])).