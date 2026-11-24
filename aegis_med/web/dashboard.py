from auditlog.models import LogEntry
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponseForbidden
from django.shortcuts import render


def home(request):
    if not request.user.is_authenticated:
        return render(request, "home/homesemlogin.html")
    return dashboard(request)


@login_required
def dashboard(request):
    activity = LogEntry.objects.select_related("actor", "content_type").order_by("-timestamp")
    if not request.user.is_admin():
        activity = activity.filter(actor=request.user)
    return render(request, "home/homecomlogin.html", {"activity": activity[:10]})


@login_required
def audit_log(request):
    if not request.user.is_admin():
        return HttpResponseForbidden("A auditoria e restrita a administradores.")

    entries = LogEntry.objects.select_related("actor", "content_type").order_by("-timestamp")

    actor = request.GET.get("actor", "").strip()
    model = request.GET.get("model", "").strip()
    action = request.GET.get("action", "").strip()

    if actor:
        entries = entries.filter(actor__username__icontains=actor)
    if model:
        entries = entries.filter(content_type__model__icontains=model)
    if action in {"0", "1", "2", "3"}:
        entries = entries.filter(action=int(action))

    paginator = Paginator(entries, 50)
    page = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "audit/list.html",
        {
            "page": page,
            "action_choices": LogEntry.Action.choices,
            "filters": {
                "actor": actor,
                "model": model,
                "action": action,
            },
        },
    )


SOURCE_CODE_URL = "https://github.com/ArcoverdePedro/AegisMed"

MODULOS = [
    (
        "users",
        "Prontuário (PEP)",
        "Cadastro SUS do paciente, encontros, evoluções com adendo e lista de problemas.",
    ),
    (
        "calendar",
        "Agenda e recepção",
        "Horários por profissional, chegada do paciente e fila de atendimento.",
    ),
    (
        "grid",
        "Internação e leitos",
        "Mapa de leitos em tempo real, admissão, transferência, alta e higienização.",
    ),
    (
        "file-text",
        "Prescrição e farmácia",
        "Prescrição estruturada, validação farmacêutica, estoque por lote e dispensação.",
    ),
    (
        "activity",
        "Enfermagem",
        "Sinais vitais e administração de medicamentos vinculada ao lote dispensado.",
    ),
    (
        "droplet",
        "Laboratório",
        "Pedidos, coleta, resultados com liberação e caixa de arquivos de equipamentos.",
    ),
    ("image", "Imagem", "Pedidos de exames de imagem e laudo com liberação e retificação."),
    (
        "package",
        "Estoque e compras",
        "Materiais, saldos, requisições, pedidos de compra e recebimento.",
    ),
    (
        "briefcase",
        "Cadastro profissional",
        "Setor, função, conselho/registro e afastamentos que bloqueiam a agenda.",
    ),
    ("clipboard", "LGPD", "Registro e acompanhamento das solicitações dos titulares de dados."),
    (
        "bar-chart-2",
        "Indicadores",
        "Ocupação de leitos, faltas, tempo de espera e qualidade de amostras.",
    ),
    ("eye", "Auditoria", "Quem acessou ou alterou o quê e quando, com filtros por usuário e ação."),
]


def sobre(request):
    modulos = [{"icone": i, "nome": n, "descricao": d} for i, n, d in MODULOS]
    return render(request, "informacoes/sobre.html", {"modulos": modulos, "fonte": SOURCE_CODE_URL})
