# ============================================================
# ESP - WEB
# ============================================================

import json
import hashlib
import os

from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, unquote
from pathlib import Path


# ============================================================
# CONFIGURACIÓN
# ============================================================

HOST = os.environ.get("HOST", "0.0.0.0")
PUERTO = int(os.environ.get("PORT", "8080"))

CARPETA_WEB = Path(__file__).resolve().parent
CARPETA_MODULOS = CARPETA_WEB / "modulos"

CARPETA_MODULOS.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# HASH DE CONTRASEÑA
# ============================================================

def hash_password(contraseña):

    return hashlib.sha256(
        str(contraseña).encode("utf-8")
    ).hexdigest()


# ============================================================
# NOMBRE SEGURO
# ============================================================

def nombre_seguro(nombre):

    if nombre is None:
        return None

    nombre = str(nombre).strip()

    if nombre.endswith(".espmod"):
        nombre = nombre[:-7]

    if not nombre:
        return None

    permitidos = (
        "abcdefghijklmnopqrstuvwxyz"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "0123456789"
        "_-"
    )

    for caracter in nombre:

        if caracter not in permitidos:
            return None

    return nombre


# ============================================================
# BUSCAR ARCHIVO DE MÓDULO
# ============================================================

def ruta_modulo(nombre):

    nombre = nombre_seguro(nombre)

    if nombre is None:
        return None

    ruta = (
        CARPETA_MODULOS /
        f"{nombre}.espmod"
    )

    return ruta


# ============================================================
# LEER MÓDULO
# ============================================================

def leer_modulo(nombre):

    ruta = ruta_modulo(nombre)

    if ruta is None:
        return None

    if not ruta.exists():
        return None

    if not ruta.is_file():
        return None

    try:

        with open(
            ruta,
            "r",
            encoding="utf-8"
        ) as archivo:

            paquete = json.load(
                archivo
            )

    except Exception:

        return None

    if not isinstance(
        paquete,
        dict
    ):

        return None

    return paquete


# ============================================================
# GUARDAR MÓDULO
# ============================================================

def guardar_modulo(paquete):

    if not isinstance(
        paquete,
        dict
    ):

        return False

    nombre = nombre_seguro(
        paquete.get("nombre")
    )

    if nombre is None:
        return False

    ruta = (
        CARPETA_MODULOS /
        f"{nombre}.espmod"
    )

    try:

        with open(
            ruta,
            "w",
            encoding="utf-8"
        ) as archivo:

            json.dump(
                paquete,
                archivo,
                ensure_ascii=False,
                indent=4
            )

        return True

    except Exception:

        return False


# ============================================================
# COMPROBAR ARCHIVOS
# ============================================================

def comprobar_archivos(paquete):

    if "archivos" not in paquete:

        return True

    archivos = paquete.get(
        "archivos"
    )

    if not isinstance(
        archivos,
        list
    ):

        return False

    for archivo in archivos:

        if not isinstance(
            archivo,
            dict
        ):

            return False

        nombre = archivo.get(
            "nombre"
        )

        contenido = archivo.get(
            "contenido"
        )

        if not isinstance(
            nombre,
            str
        ):

            return False

        if not nombre.strip():

            return False

        if not isinstance(
            contenido,
            str
        ):

            return False

    return True


# ============================================================
# LISTAR MÓDULOS PÚBLICOS
# ============================================================

def listar_modulos():

    resultado = []

    try:

        archivos = CARPETA_MODULOS.glob(
            "*.espmod"
        )

    except Exception:

        return resultado


    for archivo in archivos:

        try:

            with open(
                archivo,
                "r",
                encoding="utf-8"
            ) as f:

                paquete = json.load(f)

        except Exception:

            continue


        if not isinstance(
            paquete,
            dict
        ):

            continue


        nombre = paquete.get(
            "nombre"
        )

        visibilidad = paquete.get(
            "visibilidad",
            "publico"
        )


        if not nombre:

            continue


        # ----------------------------------------------------
        # LOS PRIVADOS NO SE MUESTRAN
        # ----------------------------------------------------

        if visibilidad != "publico":

            continue


        resultado.append({

            "nombre":
                nombre,

            "version":
                paquete.get(
                    "version",
                    1
                ),

            "cantidad_archivos":
                len(
                    paquete.get(
                        "archivos",
                        []
                    )
                )

        })


    resultado.sort(

        key=lambda modulo:
        str(
            modulo["nombre"]
        ).lower()

    )


    return resultado


# ============================================================
# SERVIDOR WEB ESP
# ============================================================

class ServidorWebESP(
    BaseHTTPRequestHandler
):


    # ========================================================
    # HEADERS
    # ========================================================

    def enviar_headers(

        self,

        codigo=200,

        tipo="application/json; charset=utf-8"

    ):

        self.send_response(
            codigo
        )

        self.send_header(
            "Content-Type",
            tipo
        )

        self.send_header(
            "Access-Control-Allow-Origin",
            "*"
        )

        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, POST, OPTIONS"
        )

        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type"
        )

        self.end_headers()


    # ========================================================
    # RESPONDER JSON
    # ========================================================

    def responder_json(

        self,

        datos,

        codigo=200

    ):

        try:

            contenido = json.dumps(

                datos,

                ensure_ascii=False

            ).encode(
                "utf-8"
            )

        except Exception:

            contenido = json.dumps({

                "error":
                    "No se pudo crear "
                    "la respuesta."

            }).encode(
                "utf-8"
            )

            codigo = 500


        self.enviar_headers(
            codigo
        )

        self.wfile.write(
            contenido
        )


    # ========================================================
    # RESPONDER ARCHIVO
    # ========================================================

    def responder_archivo(

        self,

        ruta,

        tipo

    ):

        if not ruta.exists():

            self.responder_json({

                "error":
                    "Página no encontrada."

            }, 404)

            return


        if not ruta.is_file():

            self.responder_json({

                "error":
                    "Página no encontrada."

            }, 404)

            return


        try:

            contenido = ruta.read_bytes()

        except Exception:

            self.responder_json({

                "error":
                    "No se pudo cargar "
                    "la página."

            }, 500)

            return


        self.enviar_headers(

            200,

            tipo

        )

        self.wfile.write(
            contenido
        )


    # ========================================================
    # OPTIONS
    # ========================================================

    def do_OPTIONS(self):

        self.enviar_headers(
            204
        )


    # ========================================================
    # GET
    # ========================================================

    def do_GET(self):

        ruta = urlparse(
            self.path
        )

        camino = unquote(
            ruta.path
        )


        # ====================================================
        # PÁGINA PRINCIPAL
        # ====================================================

        if camino == "/":

            self.responder_archivo(

                CARPETA_WEB /
                "index.html",

                "text/html; charset=utf-8"

            )

            return


        # ====================================================
        # OTRAS PÁGINAS
        # ====================================================

        paginas = {

            "/crear_cuenta.html":
                "crear_cuenta.html",

            "/modulo.html":
                "modulo.html",

            "/publicar.html":
                "publicar.html"

        }


        if camino in paginas:

            self.responder_archivo(

                CARPETA_WEB /
                paginas[camino],

                "text/html; charset=utf-8"

            )

            return


        # ====================================================
        # LISTA DE MÓDULOS
        # ====================================================

        if camino == "/api/modulos":

            self.responder_json({

                "correcto":
                    True,

                "modulos":
                    listar_modulos()

            })

            return


        # ====================================================
        # CONSEGUIR MÓDULO PÚBLICO
        # ====================================================

        if camino.startswith(
            "/api/modulos/"
        ):

            nombre = camino[
                len("/api/modulos/"):
            ]


            nombre = nombre_seguro(
                nombre
            )


            if nombre is None:

                self.responder_json({

                    "error":
                        "Nombre de módulo inválido."

                }, 400)

                return


            paquete = leer_modulo(
                nombre
            )


            if paquete is None:

                self.responder_json({

                    "error":
                        "El módulo no existe."

                }, 404)

                return


            visibilidad = paquete.get(

                "visibilidad",

                "publico"

            )


            if visibilidad == "privado":

                self.responder_json({

                    "error":
                        "Este módulo es privado.",

                    "privado":
                        True

                }, 403)

                return


            self.responder_json(
                paquete
            )

            return


        # ====================================================
        # RUTA DESCONOCIDA
        # ====================================================

        self.responder_json({

            "error":
                "Ruta no encontrada."

        }, 404)


    # ========================================================
    # LEER POST
    # ========================================================

    def leer_post(self):

        try:

            longitud = int(

                self.headers.get(

                    "Content-Length",

                    "0"

                )

            )

        except Exception:

            return None


        if longitud <= 0:

            return None


        try:

            datos = self.rfile.read(
                longitud
            )

            texto = datos.decode(
                "utf-8"
            )

            return json.loads(
                texto
            )

        except Exception:

            return None


    # ========================================================
    # POST
    # ========================================================

    def do_POST(self):

        ruta = urlparse(
            self.path
        )

        camino = unquote(
            ruta.path
        )


        # ====================================================
        # PUBLICAR
        # ====================================================

        if camino == "/api/publicar":

            self.publicar()

            return


        # ====================================================
        # CONSEGUIR
        # ====================================================

        if camino == "/api/conseguir":

            self.conseguir()

            return


        # ====================================================
        # DESCONOCIDO
        # ====================================================

        self.responder_json({

            "error":
                "Ruta no encontrada."

        }, 404)


    # ========================================================
    # PUBLICAR
    # ========================================================

    def publicar(self):

        paquete = self.leer_post()


        if paquete is None:

            self.responder_json({

                "error":
                    "Solicitud inválida."

            }, 400)

            return


        if not isinstance(
            paquete,
            dict
        ):

            self.responder_json({

                "error":
                    "El módulo es inválido."

            }, 400)

            return


        # ====================================================
        # COMPROBAR ESP
        # ====================================================

        if paquete.get(
            "esp_modulo"
        ) != 1:

            self.responder_json({

                "error":
                    "No es un módulo ESP válido."

            }, 400)

            return


        # ====================================================
        # NOMBRE
        # ====================================================

        nombre = nombre_seguro(

            paquete.get(
                "nombre"
            )

        )


        if nombre is None:

            self.responder_json({

                "error":
                    "El nombre del módulo "
                    "no es válido."

            }, 400)

            return


        # ====================================================
        # NOMBRE DUPLICADO
        # ====================================================

        if ruta_modulo(nombre).exists():

            self.responder_json({

                "error":
                    "Ya existe un módulo con ese nombre. "
                    "Elige otro nombre."

            }, 409)

            return


        # ====================================================
        # VISIBILIDAD
        # ====================================================

        visibilidad = paquete.get(

            "visibilidad",

            "publico"

        )


        if visibilidad not in (

            "publico",

            "privado"

        ):

            self.responder_json({

                "error":
                    "La visibilidad es inválida."

            }, 400)

            return


        # ====================================================
        # ARCHIVOS
        # ====================================================

        if not comprobar_archivos(
            paquete
        ):

            self.responder_json({

                "error":
                    "Los archivos del módulo "
                    "son inválidos."

            }, 400)

            return


        # ====================================================
        # PRIVADO
        # ====================================================

        if visibilidad == "privado":

            contraseña_hash = paquete.get(

                "contraseña_hash"

            )


            if not contraseña_hash:

                self.responder_json({

                    "error":
                        "El módulo privado "
                        "necesita contraseña."

                }, 400)

                return


            if not isinstance(

                contraseña_hash,

                str

            ):

                self.responder_json({

                    "error":
                        "La contraseña es inválida."

                }, 400)

                return


            if len(
                contraseña_hash
            ) != 64:

                self.responder_json({

                    "error":
                        "La contraseña es inválida."

                }, 400)

                return


        # ====================================================
        # PÚBLICO
        # ====================================================

        else:

            paquete[
                "contraseña_hash"
            ] = None


        # ====================================================
        # VERSIÓN
        # ====================================================

        if "version" not in paquete:

            paquete[
                "version"
            ] = 1


        # ====================================================
        # GUARDAR
        # ====================================================

        if not guardar_modulo(
            paquete
        ):

            self.responder_json({

                "error":
                    "No se pudo publicar "
                    "el módulo."

            }, 500)

            return


        # ====================================================
        # RESPUESTA
        # ====================================================

        self.responder_json({

            "correcto":
                True,

            "mensaje":
                "Módulo publicado correctamente.",

            "nombre":
                nombre,

            "visibilidad":
                visibilidad,

            "cantidad_archivos":
                len(
                    paquete.get(
                        "archivos",
                        []
                    )
                )

        })


    # ========================================================
    # CONSEGUIR
    # ========================================================

    def conseguir(self):

        solicitud = self.leer_post()


        if solicitud is None:

            self.responder_json({

                "error":
                    "Solicitud inválida."

            }, 400)

            return


        modulo = solicitud.get(
            "modulo"
        )

        contraseña = solicitud.get(
            "contraseña"
        )


        # ====================================================
        # NOMBRE
        # ====================================================

        modulo = nombre_seguro(
            modulo
        )


        if modulo is None:

            self.responder_json({

                "error":
                    "Nombre de módulo inválido."

            }, 400)

            return


        # ====================================================
        # BUSCAR
        # ====================================================

        paquete = leer_modulo(
            modulo
        )


        if paquete is None:

            self.responder_json({

                "error":
                    "El módulo no existe."

            }, 404)

            return


        visibilidad = paquete.get(

            "visibilidad",

            "publico"

        )


        # ====================================================
        # PÚBLICO
        # ====================================================

        if visibilidad == "publico":

            self.responder_json(
                paquete
            )

            return


        # ====================================================
        # PRIVADO
        # ====================================================

        if visibilidad == "privado":

            if contraseña is None:

                self.responder_json({

                    "error":
                        "Este módulo necesita "
                        "contraseña.",

                    "privado":
                        True

                }, 401)

                return


            hash_recibido = hash_password(

                contraseña

            )


            hash_guardado = paquete.get(

                "contraseña_hash"

            )


            if hash_recibido != hash_guardado:

                self.responder_json({

                    "error":
                        "Contraseña incorrecta.",

                    "privado":
                        True

                }, 403)

                return


            self.responder_json(
                paquete
            )

            return


        # ====================================================
        # VISIBILIDAD INVALIDA
        # ====================================================

        self.responder_json({

            "error":
                "Visibilidad inválida."

        }, 400)


    # ========================================================
    # LOG LIMPIO
    # ========================================================

    def log_message(
        self,
        formato,
        *argumentos
    ):

        print(
            "[ESP WEB]",
            formato % argumentos
        )


# ============================================================
# INICIAR SERVIDOR
# ============================================================

def iniciar_web():

    servidor = HTTPServer(

        (
            HOST,
            PUERTO
        ),

        ServidorWebESP

    )


    print()

    print("=" * 60)

    print(
        "                 WEB ESP"
    )

    print("=" * 60)

    print()

    print(
        f"Web: http://localhost:{PUERTO}"
    )

    print()

    print(
        "Presiona CTRL+C para detener."
    )

    print()

    print("=" * 60)

    print()


    try:

        servidor.serve_forever()

    except KeyboardInterrupt:

        print()

        print(
            "Deteniendo web ESP..."
        )

    finally:

        servidor.server_close()

        print(
            "Web ESP detenida."
        )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    iniciar_web()