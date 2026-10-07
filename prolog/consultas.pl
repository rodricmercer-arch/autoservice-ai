:- encoding(utf8).

% ============================================================
% A) SALIDA PARA EL PUENTE PYTHON (sin cambios; tabulaciones)
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

% ============================================================
% B) REPORTE FORMATEADO PARA CONSOLA (SWI-Prolog interactivo)
% Resultado = diagnostico(Fallas, Criticidad, HorasTotales, Repuestos)
%
% Consultas de ejemplo:
%   ?- emitir_diagnostico([ruido_frenos, pedal_esponjoso], R).
%   ?- emitir_diagnostico([vibracion_volante, humo_escape], R).
%   ?- emitir_diagnostico([ruido_suspension], R).
%   ?- emitir_diagnostico([ruido_inexistente], R).   % síntoma desconocido
% ============================================================

emitir_diagnostico(Sintomas,
                   diagnostico(Fallas, Crit, Horas, Reps)) :-
    diagnosticar_lista(Sintomas, Fallas),
    evaluar_criticidad_global(Fallas, Crit),
    calcular_horas_totales(Fallas, Horas),
    obtener_repuestos_necesarios(Fallas, Reps),
    exclude(sintoma_conocido, Sintomas, Desconocidos),
    linea_rep('='),
    format("  DIAGNÓSTICO AUTOSERVICE AI~n"),
    linea_rep('='),
    format("~w~t~24|~w~n", ['Síntomas recibidos:', Sintomas]),
    (   Desconocidos == []
    ->  true
    ;   format("~w~t~24|~w~n", ['Ignorados (no existen):', Desconocidos])
    ),
    linea_rep('-'),
    length(Fallas, NF),
    format("FALLAS DEDUCIDAS (~d)~n", [NF]),
    imprimir_fallas(Fallas),
    linea_rep('-'),
    format("~w~t~24|~w~n", ['Severidad global:', Crit]),
    format("~w~t~24|~1f h~n", ['Horas de mano de obra:', Horas]),
    format("REPUESTOS NECESARIOS~n"),
    imprimir_repuestos(Reps),
    linea_rep('=').

sintoma_conocido(S) :- sintoma_falla(S, _), !.

imprimir_fallas([]) :-
    format("  (ninguna falla deducida)~n").
imprimir_fallas(Fallas) :-
    Fallas \== [],
    forall(member(F, Fallas),
           ( falla_info(F, Desc, Sev, H),
             format("  ~w~t~18|[~w]~t~32|~1f h~n", [F, Sev, H]),
             format("      ~w~n", [Desc]) )).

imprimir_repuestos([]) :-
    format("  (ninguno)~n").
imprimir_repuestos(Reps) :-
    Reps \== [],
    forall(member(repuesto(C, Q), Reps),
           format("  ~w~t~18|x ~d~n", [C, Q])).

linea_rep(Car) :-
    atom_chars(Car, [C]),
    length(L, 60), maplist(=(C), L),
    atom_chars(A, L),
    format("~w~n", [A]).