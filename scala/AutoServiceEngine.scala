//> using scala 3.3.4
//> using dep com.lihaoyi::ujson:4.0.2

import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path, Paths}
import scala.math.BigDecimal.RoundingMode
import scala.util.Try

object AutoServiceEngine {

  // ===== Estructuras inmutables =====
  case class Repuesto(codigo: String, nombre: String, precio_unitario: Double, stock: Int)
  case class Servicio(codigo: String, descripcion: String, costoHora: Double)
  case class ItemCotizado(producto: Repuesto, cantidad: Int)

  case class Cotizacion(
      cotizacionId: String,
      vehiculoId: String,
      items: List[ItemCotizado],
      noEncontrados: List[String],
      costoManoObra: Double,
      subtotalGeneral: Double,
      descuentoPorcentaje: Double,
      descuentoAplicado: Double,
      baseImponible: Double,
      igvPorcentaje: Double,
      igvImpuesto: Double,
      totalNeto: Double
  )

    // ===== Entidades de registro (solo consola; NO forman parte del contrato JSON) =====
  case class Usuario(usuarioId: String, nombre: String, correo: String)
  case class Vehiculo(vehiculoId: String, placa: Option[String], sintomas: List[String])

  // Datos de demostración: reemplaza por los tuyos antes de la captura del informe.
  val UsuarioDemo: Usuario = Usuario("U-001", "Cliente de ejemplo", "cliente@example.com")

  // ===== Constantes de negocio (docs/CONTRATOS.md) =====
  val UmbralDescuento: Double = 400.0
  val DescuentoPorcentaje: Double = 10.0
  val IgvPorcentaje: Double = 18.0

  // ===== Funciones puras =====
  val calcularSubtotalItem: ItemCotizado => Double =
    item => item.producto.precio_unitario * item.cantidad

  def calcularManoObra(horas: Double, costoHora: Double): Double = horas * costoHora

  def calcularTotalSinImpuestos(items: List[ItemCotizado], costoManoObra: Double): Double =
    items.map(calcularSubtotalItem).sum + costoManoObra

  def redondear2(d: Double): Double =
    BigDecimal.decimal(d).setScale(2, RoundingMode.HALF_UP).toDouble

  // La regla devuelve el PORCENTAJE de descuento; la función devuelve el MONTO.
  val reglaDescuentoEstandar: Double => Double =
    subtotal => if (subtotal >= UmbralDescuento) DescuentoPorcentaje else 0.0

  def aplicarDescuentoDinamico(subtotalGeneral: Double, reglaDescuento: Double => Double): Double =
    subtotalGeneral * reglaDescuento(subtotalGeneral) / 100

  def filtrarRepuestosPorPrecio(inventario: List[Repuesto], criterio: Repuesto => Boolean): List[Repuesto] =
    inventario.filter(criterio)

  // ===== Función genérica polimórfica (requerimiento académico) =====
  def obtenerMaximo[T, R](lista: List[T])(criterio: T => R)(implicit ord: Ordering[R]): Option[T] = {
    if (lista.isEmpty) None else Some(lista.maxBy(criterio))
  }

  // ===== Búsqueda segura con Option =====
  def buscarRepuesto(inventario: List[Repuesto], codigo: String): Option[Repuesto] =
    inventario.find(_.codigo == codigo)

  // Devuelve (items encontrados, códigos no encontrados) sin romper el cálculo.
  def resolverItems(
      inventario: List[Repuesto],
      solicitados: List[(String, Int)]
  ): (List[ItemCotizado], List[String]) =
    solicitados.foldLeft((List.empty[ItemCotizado], List.empty[String])) {
      case ((items, faltantes), (codigo, cantidad)) =>
        buscarRepuesto(inventario, codigo) match {
          case Some(r) => (items :+ ItemCotizado(r, cantidad), faltantes)
          case None    => (items, faltantes :+ codigo)
        }
    }

  // ===== Liquidación =====
  def liquidar(
      cotizacionId: String,
      vehiculoId: String,
      items: List[ItemCotizado],
      noEncontrados: List[String],
      manoObra: Servicio,
      horas: Double
  ): Cotizacion = {
    val costoMano   = redondear2(calcularManoObra(horas, manoObra.costoHora))
    val subtotal    = redondear2(calcularTotalSinImpuestos(items, costoMano))
    val pctDesc     = reglaDescuentoEstandar(subtotal)
    val descuento   = redondear2(aplicarDescuentoDinamico(subtotal, reglaDescuentoEstandar))
    val base        = redondear2(subtotal - descuento)
    val igv         = redondear2(base * IgvPorcentaje / 100)
    val total       = redondear2(base + igv)
    Cotizacion(cotizacionId, vehiculoId, items, noEncontrados, costoMano, subtotal,
      pctDesc, descuento, base, IgvPorcentaje, igv, total)
  }

  // ===== Entrada =====
  def cargarInventario(ruta: Path): List[Repuesto] =
    ujson.read(Files.readString(ruta, UTF_8)).arr.toList
      .map(r => Repuesto(r("codigo").str, r("nombre").str, r("precio_unitario").num, r("stock").num.toInt))
      .distinctBy(_.codigo)

  // ===== Salida JSON (formato idéntico al contrato) =====
  def numJson(d: Double): String = {
    val s = BigDecimal.decimal(d).setScale(2, RoundingMode.HALF_UP).toString
    if (s.endsWith("0")) s.dropRight(1) else s
  }

  def str(s: String): String = "\"" + s.replace("\\", "\\\\").replace("\"", "\\\"") + "\""

  def detalleJson(i: ItemCotizado): String =
    s"""    {
       |      "codigo": ${str(i.producto.codigo)},
       |      "nombre": ${str(i.producto.nombre)},
       |      "precio_unitario": ${numJson(i.producto.precio_unitario)},
       |      "cantidad": ${i.cantidad},
       |      "subtotal": ${numJson(calcularSubtotalItem(i))}
       |    }""".stripMargin

  def aJson(c: Cotizacion): String = {
    val detalles =
      if (c.items.isEmpty) "[]"
      else "[\n" + c.items.map(detalleJson).mkString(",\n") + "\n  ]"
    val faltantes = "[" + c.noEncontrados.map(str).mkString(", ") + "]"
    val masCostoso = obtenerMaximo(c.items)(calcularSubtotalItem) match {
      case Some(i) =>
        s"""{
           |    "nombre": ${str(i.producto.nombre)},
           |    "subtotal": ${numJson(calcularSubtotalItem(i))}
           |  }""".stripMargin
      case None => "null"
    }
    s"""{
       |  "cotizacion_id": ${str(c.cotizacionId)},
       |  "vehiculo_id": ${str(c.vehiculoId)},
       |  "moneda": "PEN",
       |  "detalles_repuestos": $detalles,
       |  "repuestos_no_encontrados": $faltantes,
       |  "costo_mano_obra": ${numJson(c.costoManoObra)},
       |  "subtotal_general": ${numJson(c.subtotalGeneral)},
       |  "descuento_porcentaje": ${numJson(c.descuentoPorcentaje)},
       |  "descuento_aplicado": ${numJson(c.descuentoAplicado)},
       |  "base_imponible": ${numJson(c.baseImponible)},
       |  "igv_porcentaje": ${numJson(c.igvPorcentaje)},
       |  "igv_impuesto": ${numJson(c.igvImpuesto)},
       |  "total_neto": ${numJson(c.totalNeto)},
       |  "item_mas_costoso": $masCostoso
       |}""".stripMargin
  }

  // ===== Reporte de consola con f"..." =====
  def reporteConsola(c: Cotizacion, inventario: List[Repuesto]): List[String] = {
    val lineasItems = c.items.map(i =>
      f"  ${i.producto.codigo}%-8s ${i.producto.nombre}%-30s ${i.cantidad}%3d x ${i.producto.precio_unitario}%8.2f = ${calcularSubtotalItem(i)}%9.2f")
    val lineaFaltantes =
      if (c.noEncontrados.isEmpty) "  Repuestos no encontrados: ninguno"
      else s"  Repuestos no encontrados: ${c.noEncontrados.mkString(", ")}"
    val lineaMaxSubtotal = obtenerMaximo(c.items)(calcularSubtotalItem) match {
      case Some(i) => f"  Mayor subtotal : ${i.producto.nombre} (S/ ${calcularSubtotalItem(i)}%.2f)"
      case None    => "  Mayor subtotal : (sin repuestos)"
    }
    val lineaMaxCantidad = obtenerMaximo(c.items)(_.cantidad) match {
      case Some(i) => f"  Mayor cantidad : ${i.producto.nombre} (${i.cantidad}%d unidades)"
      case None    => "  Mayor cantidad : (sin repuestos)"
    }
    val economicos = filtrarRepuestosPorPrecio(inventario, _.precio_unitario <= 50.0).map(_.codigo)
    List(f"=== Cotización ${c.cotizacionId} | vehículo ${c.vehiculoId} ===") ++
      lineasItems ++
      List(
        lineaFaltantes,
        f"  Mano de obra       : S/ ${c.costoManoObra}%10.2f",
        f"  Subtotal general   : S/ ${c.subtotalGeneral}%10.2f",
        f"  Descuento (${c.descuentoPorcentaje}%.1f%%)  : S/ ${c.descuentoAplicado}%10.2f",
        f"  Base imponible     : S/ ${c.baseImponible}%10.2f",
        f"  IGV (${c.igvPorcentaje}%.1f%%)       : S/ ${c.igvImpuesto}%10.2f",
        f"  TOTAL NETO         : S/ ${c.totalNeto}%10.2f",
        lineaMaxSubtotal,
        lineaMaxCantidad,
        s"  Repuestos del inventario hasta S/ 50: ${economicos.mkString(", ")}"
      )
  }


  // ===== Registro de usuario/vehículo y severidad (solo modo consola) =====
  def leerJsonOpcional(ruta: Path): Option[ujson.Value] =
    Try(ujson.read(Files.readString(ruta, UTF_8))).toOption

  // Placa y síntomas salen de contracts/input_sintomas.json solo si es el mismo vehículo.
  def cargarVehiculo(raiz: Path, vehiculoId: String): Vehiculo = {
    val datos = leerJsonOpcional(raiz.resolve("contracts").resolve("input_sintomas.json"))
      .filter(j => Try(j("vehiculo_id").str).toOption.contains(vehiculoId))
    Vehiculo(
      vehiculoId,
      datos.flatMap(j => Try(j("placa").str).toOption),
      datos.flatMap(j => Try(j("sintomas").arr.toList.map(_.str)).toOption).getOrElse(Nil)
    )
  }

  def cargarCriticidad(raiz: Path, vehiculoId: String): Option[String] =
    leerJsonOpcional(raiz.resolve("contracts").resolve("output_diagnostico.json"))
      .filter(j => Try(j("vehiculo_id").str).toOption.contains(vehiculoId))
      .flatMap(j => Try(j("nivel_criticidad_global").str).toOption)

  def evaluarSeveridad(criticidad: Option[String]): String = criticidad match {
    case Some("urgente")  => "URGENTE - atender de inmediato, el vehículo no debería circular"
    case Some("moderada") => "MODERADA - programar la reparación en los próximos días"
    case Some("leve")     => "LEVE - puede esperar al siguiente mantenimiento"
    case Some(otra)       => s"Criticidad no reconocida: $otra"
    case None             => "Sin diagnóstico disponible para este vehículo"
  }

  def mostrarRegistro(u: Usuario, v: Vehiculo, criticidad: Option[String]): List[String] = {
    val placa      = v.placa.getOrElse("N/D")
    val sintomasTx = if (v.sintomas.isEmpty) "(sin registrar)" else v.sintomas.mkString(", ")
    List(
      "=== REGISTRO DE USUARIO Y VEHÍCULO ===",
      f"  Usuario    : ${u.nombre}%-24s (ID ${u.usuarioId}, ${u.correo})",
      f"  Vehículo   : ${v.vehiculoId}%-24s Placa: $placa%s",
      s"  Síntomas   : $sintomasTx",
      s"  Criticidad : ${evaluarSeveridad(criticidad)}"
    )
  }


  // ===== Punto de entrada =====
  // args: [raiz] [entrada] [salida]  (rutas de entrada/salida relativas a la raíz)
  def main(args: Array[String]): Unit = {
    java.util.Locale.setDefault(java.util.Locale.US)
    val raiz        = Paths.get(args.headOption.getOrElse("."))
    val rutaEntrada = raiz.resolve(args.lift(1).getOrElse("contracts/input_cotizacion.json"))
    val rutaSalida  = raiz.resolve(args.lift(2).getOrElse("contracts/output_cotizacion.json"))

    val inventarioRepuestos: List[Repuesto] =
      cargarInventario(raiz.resolve("data").resolve("inventario_repuestos.json"))

    val entrada = ujson.read(Files.readString(rutaEntrada, UTF_8))
    val solicitados = entrada("repuestos").arr.toList
      .map(r => (r("codigo").str, r("cantidad").num.toInt))
    val manoObra = Servicio("MO-GENERAL", "Mano de obra", entrada("costo_hora_mano_obra").num)

    val (items, noEncontrados) = resolverItems(inventarioRepuestos, solicitados)
    val cotizacion = liquidar(
      entrada("cotizacion_id").str,
      entrada("vehiculo_id").str,
      items,
      noEncontrados,
      manoObra,
      entrada("horas_mano_obra").num
    )

        if (args.nonEmpty) {
      // Modo CLI (ejecutar_cotizacion.py / FastAPI): solo el JSON del contrato.
      Files.writeString(rutaSalida, aJson(cotizacion) + "\n", UTF_8)
      println(s"OK: ${rutaSalida}")
    } else {
      // Modo consola (scala-cli run scala/): reporte visual; no escribe contratos.
      val vehiculo   = cargarVehiculo(raiz, cotizacion.vehiculoId)
      val criticidad = cargarCriticidad(raiz, cotizacion.vehiculoId)
      val lineas = mostrarRegistro(UsuarioDemo, vehiculo, criticidad) ++ List("") ++
        reporteConsola(cotizacion, inventarioRepuestos)
      lineas.foreach(println)
    }
  }
}