:- encoding(utf8).
:- use_module(library(lists)).
:- use_module(library(apply)).

% ============================================================
% VISTAS DE COMPATIBILIDAD (no son hechos)
% ============================================================

% falla_info(CodigoFalla, Descripcion, Severidad, HorasManoObra)
falla_info(F, Desc, Sev, Horas) :-
    falla_descripcion(F, Desc),
    severidad_falla(F, Sev),
    horas_estimadas(F, Horas).

% repuesto_necesario(CodigoFalla, CodigoRepuesto)
repuesto_necesario(F, Cod) :- falla_repuesto(F, Cod, _).

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