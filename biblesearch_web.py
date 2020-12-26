from gi import require_version as gi_require_version
gi_require_version('Gtk', '3.0')
gi_require_version('WebKit2', '4.0')


def server_proc():
    """ Create a process for the webserver and return the process.

    """

    from socket import gethostname, gethostbyname
    from multiprocessing import Process

    import biblesearch_app

    return Process(target=biblesearch_app.bible_app.run,
                   kwargs={"host":gethostbyname(gethostname()), "port":8081,
                           "server":"tornado"})

def webkit_window(url: str = 'http://127.0.1.1:8081', width: int = 1280,
                  height: int = 720):
    """ Open the biblesearch webpage in a simple webkit window.

    """

    from gi.repository import WebKit2
    from gi.repository import Gtk
    import os

    proc = server_proc()
    proc.start()

    webview = WebKit2.WebView()
    settings = webview.get_settings()
    settings.set_property('user-agent', '''Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.106 Safari/537.36''')
    webview.load_uri(url)

    scroll = Gtk.ScrolledWindow()
    scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
    scroll.set_shadow_type(Gtk.ShadowType.IN)
    scroll.add(webview)

    window = Gtk.Window()
    window.set_default_icon_from_file(f'{os.path.dirname(__file__)}/assets/ico/biblesearch-48x48.svg')
    window.set_size_request(width, height)
    window.set_title('Biblesearch')
    window.connect_after('destroy', Gtk.main_quit)
    window.add(scroll)
    window.show_all()

    Gtk.main()

    proc.terminate()
    proc.join()

if __name__ == "__main__":
    webkit_window()
