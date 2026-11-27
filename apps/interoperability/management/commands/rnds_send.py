from collections import Counter

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.interoperability import rnds
from apps.interoperability.models import RndsSubmission


class Command(BaseCommand):
    help = "Enfileira resultados liberados de exames codificados e envia à RNDS (rodar no cron)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Só monta os documentos e conta bloqueios; não grava nem envia.",
        )
        parser.add_argument(
            "--reset-failed",
            action="store_true",
            help="Zera tentativas dos envios que esgotaram as repetições.",
        )
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args, dry_run, reset_failed, limit, **options):
        if not settings.RNDS_SEND_SINCE:
            raise CommandError("Defina RNDS_SEND_SINCE (AAAA-MM-DD).")
        if dry_run:
            return self._dry_run(limit)
        if not settings.RNDS_ENABLED:
            raise CommandError("RNDS desligada (RNDS_ENABLED=false). Use --dry-run para conferir.")
        if reset_failed:
            reset = RndsSubmission.objects.filter(status=RndsSubmission.Status.FAILED).update(
                attempts=0
            )
            self.stdout.write(f"Tentativas zeradas: {reset}.")
        queued = rnds.queue_released_results()
        outcome = rnds.send_pending(limit=limit)
        summary = ", ".join(f"{status}={count}" for status, count in sorted(outcome.items()))
        self.stdout.write(f"Enfileirados: {queued}. Processados: {summary or 'nenhum'}.")

    def _dry_run(self, limit):
        reasons = Counter()
        for result in rnds._results_to_queue()[:limit]:
            try:
                rnds.build_bundle(result, document_key="dry-run")
            except rnds.RndsBlocked as exc:
                reasons[str(exc)] += 1
            else:
                reasons["Pronto para envio"] += 1
        for reason, count in reasons.most_common():
            self.stdout.write(f"{count:5d}  {reason}")
        if not reasons:
            self.stdout.write("Nenhum resultado elegível.")
