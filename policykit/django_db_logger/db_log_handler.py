import logging

db_default_formatter = logging.Formatter()


class DatabaseLogHandler(logging.Handler):
    def emit(self, record):
        from .models import EvaluationLog

        trace = None

        if record.exc_info:
            trace = db_default_formatter.formatException(record.exc_info)

        msg = self.format(record)

        community = record.args.get("community")
        proposal = record.args.get("proposal")
        kwargs = {
            "logger_name": record.name,
            "level": record.levelno,
            "msg": msg,
            "trace": trace,
            "community": community,
            "proposal": proposal,
            # Include stringified versions of action and policy so they remain if when the eval is deleted
            "policy_str": str(proposal.policy) if proposal else None,
            "action_str": str(proposal.action) if proposal else None,
        }

        EvaluationLog.objects.create(**kwargs)

    def format(self, record):
        if self.formatter:
            fmt = self.formatter
        else:
            fmt = db_default_formatter

        if type(fmt) == logging.Formatter:
            record.message = record.getMessage()

            if fmt.usesTime():
                record.asctime = fmt.formatTime(record, fmt.datefmt)

            # ignore exception traceback and stack info

            return fmt.formatMessage(record)
        else:
            return fmt.format(record)