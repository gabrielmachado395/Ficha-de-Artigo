import json
import os
import sys
import unicodedata
import base64
from pprint import pprint

import win32print

# Imports pesados (Pillow/qrcode/win32ui) são carregados apenas nos modos GDI.

PESO_LABEL = "Peso (KG)"
TAMBORES_LABEL = "Tambores"
DEFAULT_PRINTER = r"ELGIN i8"
CAIXA_SEM_PADRAO = "Sem padrão"


def _list_printer_names():
    flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
    printers = win32print.EnumPrinters(flags)
    # EnumPrinters retorna tuplas; o nome fica na posição 2
    names = []
    for p in printers:
        try:
            name = str(p[2] or "").strip()
        except Exception:
            name = ""
        if name:
            names.append(name)
    return names


def _get_default_printer_name():
    try:
        name = win32print.GetDefaultPrinter()
        return str(name or "").strip()
    except Exception:
        return ""


def _normalize_printer_name(name: str) -> str:
    # Ajuda a casar nomes como "ELGIN i8" vs "ELGIN i8 (copy 1)".
    s = str(name or "").strip().lower()
    if not s:
        return ""
    for suffix in (" (copy 1)", " (copy 2)", " (copy 3)", " (copy 4)", " (copy 5)"):
        if s.endswith(suffix):
            s = s[: -len(suffix)].strip()
            break
    return s


def _build_printer_candidates(preferred: str):
    preferred = str(preferred or "").strip()
    installed = _list_printer_names()
    default_name = _get_default_printer_name()

    norm_pref = _normalize_printer_name(preferred)
    candidates = []

    def add(n):
        n = str(n or "").strip()
        if n and n not in candidates:
            candidates.append(n)

    # 1) preferida literal
    add(preferred)

    # 2) match por normalização (ex: "ELGIN i8" -> "ELGIN i8 (copy 1)")
    if norm_pref:
        for n in installed:
            if _normalize_printer_name(n) == norm_pref:
                add(n)

        # 3) startswith (caso tenha sufixos diferentes)
        for n in installed:
            if n.lower().startswith(preferred.lower()):
                add(n)

    # 4) impressora padrão do Windows
    add(default_name)

    # 5) fallback final: primeira instalada
    if installed:
        add(installed[0])

    return [c for c in candidates if c]


def _select_printer_name(preferred: str):
    """Escolhe uma impressora que exista e não esteja em PendingDeletion.

    Retorna (selected_name, candidates).
    """
    candidates = _build_printer_candidates(preferred)
    pending_deletion_flag = getattr(win32print, "PRINTER_STATUS_PENDING_DELETION", None)

    for candidate in candidates:
        handle = None
        try:
            handle = win32print.OpenPrinter(candidate)
            if pending_deletion_flag is not None:
                try:
                    info = win32print.GetPrinter(handle, 2)
                    status = int((info or {}).get("Status") or 0)
                    if status & int(pending_deletion_flag):
                        continue
                except Exception:
                    # Se não der pra ler status, não bloqueia.
                    pass
            return candidate, candidates
        except Exception:
            continue
        finally:
            try:
                if handle is not None:
                    win32print.ClosePrinter(handle)
            except Exception:
                pass

    return str(preferred or "").strip(), candidates


def remover_acentos(texto):
    if texto is None:
        return ""
    return (
        unicodedata.normalize("NFKD", str(texto))
        .encode("ASCII", "ignore")
        .decode("ASCII")
    )


def split_text(text, max_width, hdc):
    words = str(text or "").split(" ")
    lines = []
    current_line = ""

    for word in words:
        test_line = current_line + (" " if current_line else "") + word
        size = hdc.GetTextExtent(test_line)
        if size[0] <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    return lines


def _required_fields_tingimento(order_data):
    required_field_keys = [
        "Ordem",
        "Artigo",
        "Cor",
        PESO_LABEL,
        TAMBORES_LABEL,
        "Operador",
        "Data Tingimento",
    ]

    missing = []

    for key in required_field_keys:
        value_str = str(order_data.get(key, "")).strip()
        if not value_str:
            missing.append(key)
            continue

        if key == "Operador" and (
            "não encontrado" in value_str.lower() or "inválida" in value_str.lower()
        ):
            missing.append("Operador (Inválido)")
            continue

        if key in [PESO_LABEL, TAMBORES_LABEL, "Quant. Cópias"]:
            try:
                numeric_value = float(value_str.replace(",", "."))
                if numeric_value <= 0.0:
                    missing.append(f"{key} (> 0)")
            except ValueError:
                missing.append(f"{key} (Inválido/Não Numérico)")

    return sorted(set(missing))


def build_order_data(payload):
    tab = (payload or {}).get("tab") or "tingimento"
    order = (payload or {}).get("order") or {}

    # Campos comuns
    ordem = order.get("ordem", "")
    artigo = order.get("artigo", "")
    cor = order.get("cor", "")
    cliente = order.get("cliente", "")
    volume_prog = order.get("volume", "")

    # Campos do formulário React
    data_processo = payload.get("dataProcesso", "")
    elasticidade = payload.get("elasticidadeAcab", "")
    largura = payload.get("larguraAcab", "")
    mtf = payload.get("mtf", "")
    num_cortes = payload.get("numeroCortes", "")
    operador = payload.get("operador", "")
    turno = payload.get("turno", "")
    tambores = payload.get("tambores", "")
    caixa = payload.get("caixa", "") or CAIXA_SEM_PADRAO
    peso = payload.get("pesoKg", "")
    metros = payload.get("metros", "0.00")
    distribuicao = payload.get("distribuicao", "0.00")
    obs = payload.get("observacoes", "")

    if tab == "retingimento":
        # Mantém as chaves que o print_reprocesso usa no QR
        order_data = {
            "Artigo": str(artigo),
            "Cor": str(cor),
            "Volume Prog": str(volume_prog),
            "Data Tingimento": str(payload.get("dataTingimento", "")),
            "Elasticidade Acab": str(elasticidade),
            "Largura Acab": str(largura),
            "Cliente": str(cliente),
            "MTF": str(mtf),
            "Nº Cortes": str(num_cortes),
            "Operador": str(operador),
            "Turno": str(turno),
            TAMBORES_LABEL: str(tambores),
            "Caixa": str(caixa),
            PESO_LABEL: str(peso),
            "Metros": str(metros),
            "Data Retingimento": str(data_processo),
            "Observações": str(obs),
        }
        return {k: (v.upper() if isinstance(v, str) else v) for k, v in order_data.items()}

    # Tingimento (ordem completa)
    order_data = {
        "Ordem": str(ordem),
        "Artigo": str(artigo),
        "Cor": str(cor),
        "Volume Prog": str(volume_prog),
        "Data Tingimento": str(data_processo),
        "Elasticidade Acab": str(elasticidade),
        "Largura Acab": str(largura),
        "Cliente": str(cliente),
        "MTF": str(mtf),
        "Nº Cortes": str(num_cortes),
        "Operador": str(operador),
        "Turno": str(turno),
        TAMBORES_LABEL: str(tambores),
        "Caixa": str(caixa),
        PESO_LABEL: str(peso),
        "Metros": str(metros),
        "Observações": str(obs),
    }
    return {k: (v.upper() if isinstance(v, str) else v) for k, v in order_data.items()}


def print_order(order_data, printer_name=DEFAULT_PRINTER, pedido_especial=""):
    import win32ui
    from PIL import Image, ImageWin
    import qrcode

    if not order_data.get("Caixa", "").strip():
        order_data["Caixa"] = CAIXA_SEM_PADRAO

    missing_fields = _required_fields_tingimento(order_data)
    if missing_fields:
        raise ValueError(
            "Não é possível imprimir. Campos obrigatórios ausentes/ inválidos:\n\n"
            + "\n".join(f"- {c}" for c in missing_fields)
        )

    selected_printer, candidates = _select_printer_name(printer_name)
    last_error = None

    printer_handle = None
    try:
        printer_handle = win32print.OpenPrinter(selected_printer)
        hdc = win32ui.CreateDC()
        hdc.CreatePrinterDC(selected_printer)

        if pedido_especial and str(pedido_especial).upper() == "SIM":
            titulo = "Ficha de Artigo     *** Pedido Especial ***"
        else:
            titulo = "Ficha do Artigo"

        hdc.StartDoc(titulo)
        hdc.StartPage()

        pos_inicial_x = 30
        pos_inicial_y = 50
        largura_celula_nome = 250
        largura_celula_valor = 290
        altura_celula = 50

        hdc.TextOut(pos_inicial_x, pos_inicial_y, titulo)
        pos_inicial_y += 50

        for label, value in order_data.items():
            value = "" if value is None else str(value)

            # caixa do label
            hdc.MoveTo(pos_inicial_x, pos_inicial_y)
            hdc.LineTo(pos_inicial_x + largura_celula_nome, pos_inicial_y)
            hdc.LineTo(
                pos_inicial_x + largura_celula_nome, pos_inicial_y + altura_celula
            )
            hdc.LineTo(pos_inicial_x, pos_inicial_y + altura_celula)
            hdc.LineTo(pos_inicial_x, pos_inicial_y)

            # caixa do valor
            hdc.MoveTo(pos_inicial_x + largura_celula_nome, pos_inicial_y)
            hdc.LineTo(
                pos_inicial_x + largura_celula_nome + largura_celula_valor,
                pos_inicial_y,
            )
            hdc.LineTo(
                pos_inicial_x + largura_celula_nome + largura_celula_valor,
                pos_inicial_y + altura_celula,
            )
            hdc.LineTo(
                pos_inicial_x + largura_celula_nome, pos_inicial_y + altura_celula
            )

            hdc.TextOut(pos_inicial_x + 10, pos_inicial_y + 15, str(label))

            if label == "Cor":
                if any(x in value.lower() for x in ["enfestado", "enfraldado"]):
                    palavra_especial = None
                    for termo in ["enfestado", "enfraldado"]:
                        if termo in value.lower():
                            palavra_especial = termo
                            break

                    if palavra_especial:
                        index = value.lower().find(palavra_especial)
                        texto_antes = value[:index].rstrip()
                        texto_depois = value[index:].lstrip()

                        hdc.TextOut(
                            pos_inicial_x + largura_celula_nome + 10,
                            pos_inicial_y + 15,
                            texto_antes,
                        )
                        pos_inicial_y += altura_celula

                        # segunda linha
                        hdc.MoveTo(pos_inicial_x, pos_inicial_y)
                        hdc.LineTo(pos_inicial_x + largura_celula_nome, pos_inicial_y)
                        hdc.LineTo(
                            pos_inicial_x + largura_celula_nome,
                            pos_inicial_y + altura_celula,
                        )
                        hdc.LineTo(pos_inicial_x, pos_inicial_y + altura_celula)
                        hdc.LineTo(pos_inicial_x, pos_inicial_y)

                        hdc.MoveTo(pos_inicial_x + largura_celula_nome, pos_inicial_y)
                        hdc.LineTo(
                            pos_inicial_x + largura_celula_nome + largura_celula_valor,
                            pos_inicial_y,
                        )
                        hdc.LineTo(
                            pos_inicial_x + largura_celula_nome + largura_celula_valor,
                            pos_inicial_y + altura_celula,
                        )
                        hdc.LineTo(
                            pos_inicial_x + largura_celula_nome,
                            pos_inicial_y + altura_celula,
                        )

                        hdc.TextOut(
                            pos_inicial_x + largura_celula_nome + 10,
                            pos_inicial_y + 15,
                            texto_depois,
                        )
                        pos_inicial_y += altura_celula
                        continue

                linhas_texto = split_text(value, largura_celula_valor - 20, hdc)
                if linhas_texto:
                    hdc.TextOut(
                        pos_inicial_x + largura_celula_nome + 10,
                        pos_inicial_y + 15,
                        linhas_texto[0],
                    )
                    pos_inicial_y += altura_celula

                    for linha in linhas_texto[1:]:
                        hdc.MoveTo(pos_inicial_x, pos_inicial_y)
                        hdc.LineTo(pos_inicial_x + largura_celula_nome, pos_inicial_y)
                        hdc.LineTo(
                            pos_inicial_x + largura_celula_nome,
                            pos_inicial_y + altura_celula,
                        )
                        hdc.LineTo(pos_inicial_x, pos_inicial_y + altura_celula)
                        hdc.LineTo(pos_inicial_x, pos_inicial_y)

                        hdc.MoveTo(pos_inicial_x + largura_celula_nome, pos_inicial_y)
                        hdc.LineTo(
                            pos_inicial_x + largura_celula_nome + largura_celula_valor,
                            pos_inicial_y,
                        )
                        hdc.LineTo(
                            pos_inicial_x + largura_celula_nome + largura_celula_valor,
                            pos_inicial_y + altura_celula,
                        )
                        hdc.LineTo(
                            pos_inicial_x + largura_celula_nome,
                            pos_inicial_y + altura_celula,
                        )

                        hdc.TextOut(
                            pos_inicial_x + largura_celula_nome + 10,
                            pos_inicial_y + 15,
                            linha,
                        )
                        pos_inicial_y += altura_celula

                hdc.MoveTo(pos_inicial_x, pos_inicial_y)
                hdc.LineTo(
                    pos_inicial_x + largura_celula_nome + largura_celula_valor,
                    pos_inicial_y,
                )
                pos_inicial_y += 5
                continue

            if label == "Cliente":
                linhas_texto = split_text(value, largura_celula_valor - 20, hdc)
                if linhas_texto:
                    hdc.TextOut(
                        pos_inicial_x + largura_celula_nome + 10,
                        pos_inicial_y + 15,
                        linhas_texto[0],
                    )
                    pos_inicial_y += altura_celula

                    for linha in linhas_texto[1:]:
                        hdc.MoveTo(pos_inicial_x, pos_inicial_y)
                        hdc.LineTo(pos_inicial_x + largura_celula_nome, pos_inicial_y)
                        hdc.LineTo(
                            pos_inicial_x + largura_celula_nome,
                            pos_inicial_y + altura_celula,
                        )
                        hdc.LineTo(pos_inicial_x, pos_inicial_y + altura_celula)
                        hdc.LineTo(pos_inicial_x, pos_inicial_y)

                        hdc.MoveTo(pos_inicial_x + largura_celula_nome, pos_inicial_y)
                        hdc.LineTo(
                            pos_inicial_x + largura_celula_nome + largura_celula_valor,
                            pos_inicial_y,
                        )
                        hdc.LineTo(
                            pos_inicial_x + largura_celula_nome + largura_celula_valor,
                            pos_inicial_y + altura_celula,
                        )
                        hdc.LineTo(
                            pos_inicial_x + largura_celula_nome,
                            pos_inicial_y + altura_celula,
                        )

                        hdc.TextOut(
                            pos_inicial_x + largura_celula_nome + 10,
                            pos_inicial_y + 15,
                            linha,
                        )
                        pos_inicial_y += altura_celula

                hdc.MoveTo(pos_inicial_x, pos_inicial_y)
                hdc.LineTo(
                    pos_inicial_x + largura_celula_nome + largura_celula_valor,
                    pos_inicial_y,
                )
                pos_inicial_y += 5
                continue

            hdc.TextOut(pos_inicial_x + largura_celula_nome + 10, pos_inicial_y + 15, value)
            pos_inicial_y += altura_celula

        qr_data = {
            "Ordem": remover_acentos(order_data.get("Ordem")),
            "VolumeProg": remover_acentos(order_data.get("Volume Prog", "")),
            "Artigo": remover_acentos(order_data.get("Artigo")),
            "Cor": remover_acentos(order_data.get("Cor")),
            "Tambores": remover_acentos(order_data.get(TAMBORES_LABEL)),
            "Caixa": remover_acentos(order_data.get("Caixa")),
            "Peso": remover_acentos(order_data.get(PESO_LABEL)),
            "Metros": remover_acentos(order_data.get("Metros")),
            "DataTingimento": order_data.get("Data Tingimento", ""),
            "NumCorte": order_data.get("Nº Cortes", ""),
        }

        qr_json = json.dumps(qr_data)

        pasta_qr = "qrcodes"
        if not os.path.exists(pasta_qr):
            os.makedirs(pasta_qr)

        caminho_qr = os.path.join(pasta_qr, "qrcode.png")
        caminho_json = os.path.join(pasta_qr, "dados.json")

        with open(caminho_json, "w", encoding="utf-8") as f_json:
            f_json.write(qr_json)

        qr_imagem = qrcode.make(qr_json)
        qr_imagem.save(caminho_qr)

        page_width = hdc.GetDeviceCaps(110)
        tamanho_qr = 400
        pos_qr_x = (page_width - tamanho_qr) // 2
        pos_qr_y = pos_inicial_y + 20

        imagem_qr = Image.open(caminho_qr)
        dib = ImageWin.Dib(imagem_qr)
        dib.draw(
            hdc.GetHandleOutput(),
            (pos_qr_x, pos_qr_y, pos_qr_x + tamanho_qr, pos_qr_y + tamanho_qr),
        )

        hdc.EndPage()
        hdc.EndDoc()
        hdc.DeleteDC()

        print("Impressão realizada com sucesso!")
        print("DADOS PARA IMPRESSÃO:")
        pprint(order_data)
        return
    except Exception as e:
        last_error = e
    finally:
        try:
            if printer_handle is not None:
                win32print.ClosePrinter(printer_handle)
        except Exception:
            pass

    available = _list_printer_names()
    default_name = _get_default_printer_name()
    raise RuntimeError(
        "Falha ao imprimir no Windows. "
        f"Impressora solicitada: '{printer_name}'. "
        f"Selecionada: '{selected_printer}'. "
        f"Padrão do Windows: '{default_name}'. "
        f"Candidatas tentadas: {candidates}. "
        f"Instaladas: {available}. "
        f"Erro: {str(last_error or 'desconhecido')}"
    )


def print_reprocesso(order_data, printer_name=DEFAULT_PRINTER):
    import win32ui
    from PIL import Image, ImageWin
    import qrcode

    selected_printer, candidates = _select_printer_name(printer_name)
    last_error = None

    printer_handle = None
    try:
        printer_handle = win32print.OpenPrinter(selected_printer)
        hdc = win32ui.CreateDC()
        hdc.CreatePrinterDC(selected_printer)

        titulo = "Retingimento - Ficha do Artigo"

        hdc.StartDoc(titulo)
        hdc.StartPage()

        hdc.TextOut(10, 10, titulo)

        pos_inicial_x = 30
        pos_inicial_y = 50
        largura_celula_nome = 250
        largura_celula_valor = 290
        altura_celula = 50

        for label, value in order_data.items():
            value = "" if value is None else str(value)

            hdc.MoveTo(pos_inicial_x, pos_inicial_y)
            hdc.LineTo(pos_inicial_x + largura_celula_nome, pos_inicial_y)
            hdc.LineTo(
                pos_inicial_x + largura_celula_nome, pos_inicial_y + altura_celula
            )
            hdc.LineTo(pos_inicial_x, pos_inicial_y + altura_celula)
            hdc.LineTo(pos_inicial_x, pos_inicial_y)

            hdc.MoveTo(pos_inicial_x + largura_celula_nome, pos_inicial_y)
            hdc.LineTo(
                pos_inicial_x + largura_celula_nome + largura_celula_valor, pos_inicial_y
            )
            hdc.LineTo(
                pos_inicial_x + largura_celula_nome + largura_celula_valor,
                pos_inicial_y + altura_celula,
            )
            hdc.LineTo(pos_inicial_x + largura_celula_nome, pos_inicial_y)

            hdc.TextOut(pos_inicial_x + 10, pos_inicial_y + 15, str(label))
            hdc.TextOut(
                pos_inicial_x + largura_celula_nome + 10, pos_inicial_y + 15, value
            )

            pos_inicial_y += altura_celula

        qr_data = {
            "VolumeProg": remover_acentos(order_data.get("Volume Prog", "")),
            "Artigo": remover_acentos(order_data.get("Artigo")),
            "Cor": remover_acentos(order_data.get("Cor")),
            "Tambores": remover_acentos(order_data.get(TAMBORES_LABEL)),
            "Caixa": remover_acentos(order_data.get("Caixa")),
            "Peso": remover_acentos(order_data.get(PESO_LABEL)),
            "Metros": remover_acentos(order_data.get("Metros")),
            "DataTingimento": order_data.get("Data Tingimento", ""),
            "NumCorte": order_data.get("Nº Cortes", ""),
        }

        qr_json = json.dumps(qr_data)

        pasta_qr = "qrcodes"
        if not os.path.exists(pasta_qr):
            os.makedirs(pasta_qr)

        caminho_qr = os.path.join(pasta_qr, "qrcode_reprocesso.png")
        caminho_json = os.path.join(pasta_qr, "dados_reprocesso.json")

        with open(caminho_json, "w", encoding="utf-8") as f_json:
            f_json.write(qr_json)

        qr_imagem = qrcode.make(qr_json)
        qr_imagem.save(caminho_qr)

        page_width = hdc.GetDeviceCaps(110)
        tamanho_qr = 350
        pos_qr_x = (page_width - tamanho_qr) // 2
        pos_qr_y = pos_inicial_y + 20

        imagem_qr = Image.open(caminho_qr)
        dib = ImageWin.Dib(imagem_qr)
        dib.draw(
            hdc.GetHandleOutput(),
            (pos_qr_x, pos_qr_y, pos_qr_x + tamanho_qr, pos_qr_y + tamanho_qr),
        )

        hdc.EndPage()
        hdc.EndDoc()
        hdc.DeleteDC()

        print("Impressão (reprocesso) realizada com sucesso!")
        print("DADOS PARA IMPRESSÃO:")
        pprint(order_data)
        return
    except Exception as e:
        last_error = e
    finally:
        try:
            if printer_handle is not None:
                win32print.ClosePrinter(printer_handle)
        except Exception:
            pass

    available = _list_printer_names()
    default_name = _get_default_printer_name()
    raise RuntimeError(
        "Falha ao imprimir no Windows (reprocesso). "
        f"Impressora solicitada: '{printer_name}'. "
        f"Selecionada: '{selected_printer}'. "
        f"Padrão do Windows: '{default_name}'. "
        f"Candidatas tentadas: {candidates}. "
        f"Instaladas: {available}. "
        f"Erro: {str(last_error or 'desconhecido')}"
    )


def print_raw_escpos(raw_base64: str, printer_name=DEFAULT_PRINTER, title="Ficha do Artigo"):
    selected_printer, candidates = _select_printer_name(printer_name)
    last_error = None
    printer_handle = None

    try:
        if not raw_base64:
            raise ValueError("Payload rawEscPosBase64 vazio")

        try:
            data = base64.b64decode(raw_base64, validate=False)
        except Exception as e:
            raise ValueError(f"Falha ao decodificar base64 do ESC/POS: {str(e)}")

        printer_handle = win32print.OpenPrinter(selected_printer)

        # type = RAW -> manda bytes direto para a impressora (mesmo formato do APK TCP/9100)
        docinfo = (str(title or "Etiqueta"), None, "RAW")
        job = win32print.StartDocPrinter(printer_handle, 1, docinfo)
        try:
            win32print.StartPagePrinter(printer_handle)
            try:
                win32print.WritePrinter(printer_handle, data)
            finally:
                win32print.EndPagePrinter(printer_handle)
        finally:
            win32print.EndDocPrinter(printer_handle)

        print("Impressão RAW (ESC/POS) realizada com sucesso!")
        return
    except Exception as e:
        last_error = e
    finally:
        try:
            if printer_handle is not None:
                win32print.ClosePrinter(printer_handle)
        except Exception:
            pass

    available = _list_printer_names()
    default_name = _get_default_printer_name()
    raise RuntimeError(
        "Falha ao imprimir no Windows (RAW ESC/POS). "
        f"Impressora solicitada: '{printer_name}'. "
        f"Selecionada: '{selected_printer}'. "
        f"Padrão do Windows: '{default_name}'. "
        f"Candidatas tentadas: {candidates}. "
        f"Instaladas: {available}. "
        f"Erro: {str(last_error or 'desconhecido')}"
    )


def main():
    payload_bytes = sys.stdin.buffer.read()
    if not payload_bytes:
        payload = {}
    else:
        # Node/Electron envia UTF-8; garante que acentos (ex: "Falcão") não virem lixo.
        for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
            try:
                payload_text = payload_bytes.decode(enc)
                payload = json.loads(payload_text or "{}")
                break
            except Exception:
                payload = None
        if payload is None:
            raise ValueError("Não foi possível decodificar o payload JSON.")

    tab = (payload.get("tab") or "tingimento").strip().lower()

    # Permite escolher impressora por payload (desktop). Se não vier, usa DEFAULT_PRINTER.
    # Ex: payload.printerName = "ELGIN i8 (copy 1)"
    printer_name = (payload.get("printerName") or payload.get("printer") or "").strip() or DEFAULT_PRINTER

    # Desktop: se vier ESC/POS em base64, imprime em RAW para ficar igual ao APK.
    raw_escpos_b64 = (payload.get("rawEscPosBase64") or payload.get("escposBase64") or "").strip()
    if raw_escpos_b64:
        title = "Retingimento - Ficha do Artigo" if tab == "retingimento" else "Ficha do Artigo"
        print_raw_escpos(raw_escpos_b64, printer_name=printer_name, title=title)
        sys.stdout.write(json.dumps({"ok": True, "via": "raw-escpos"}))
        return

    order_data = build_order_data(payload)

    if tab == "retingimento":
        print_reprocesso(order_data, printer_name=printer_name)
    else:
        pedido_especial = (payload.get("order") or {}).get("pedidoEspecial") or ""
        print_order(order_data, printer_name=printer_name, pedido_especial=pedido_especial)

    sys.stdout.write(json.dumps({"ok": True}))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        sys.stderr.write(str(e))
        sys.exit(1)
