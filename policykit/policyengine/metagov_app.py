from metagov.core.app import MetagovApp
from metagov.core.handlers import MetagovRequestHandler

metagov = MetagovApp()
metagov_handler = MetagovRequestHandler(metagov)