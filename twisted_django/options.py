import sys
from optparse import OptionParser


def get_options():
    parser = OptionParser()
    parser.add_option("-n", "--projectname", dest="project",
                      help="Name of project", default=None)
    parser.add_option("-p", "--port", dest="port",
                      help="Port number", default="8080")
    parser.add_option("-f", "--path", dest="path",
                      help="The full path of the django project")
    parser.add_option("-d", "--debug", action="store_true", dest="debug", default=False)
    (options, args) = parser.parse_args()

    if not options.project:
        print "Error: no project name specified"
        sys.exit(1)

    return (options, args)
