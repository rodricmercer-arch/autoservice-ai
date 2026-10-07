:- encoding(utf8).
% Punto de entrada único. Las rutas relativas se resuelven respecto a
% la carpeta de este archivo, así funciona desde cualquier cwd.
:- consult([hechos, reglas, consultas]).