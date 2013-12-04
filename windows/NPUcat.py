#encoding:utf-8

'''
NPUcat is a one-key HTTP proxy based on xiaoxia's excellent work, please refer to:
    http://xiaoxia.org/2011/11/14/update-sogou-proxy-program-with-https-support/

'''

from Tkinter import Tk, Menu, Toplevel, Label, IntVar
import os
import time
import threading
import _winreg as winreg, ctypes
import proxy
import ConfigParser, codecs

class NPUcat:
    def __init__(self):        
        self.root = root = Tk()
        root.tk.call('package', 'require', 'Winico')
        self.icon = icon = root.tk.call('winico', 'createfrom', os.path.join(os.getcwd(), 'icon.ico'))
        root.tk.call('winico', 'taskbar', 'add', icon,    # Add trayicon
                     '-callback', (root.register(self.callback_func), '%m', '%x', '%y'),
                     '-pos',0, '-text',u'西工大的猫 1.3')
        self.menu = menu = Menu(root, tearoff=0)    # Add popup menu
        self.proxy_state = IntVar()
        menu.add_checkbutton(label=u'启用代理', variable=self.proxy_state,command=self.cmd_start_proxy)
        menu.add_separator()
        menu.add_command(label=u'配置文件', command=self.cmd_settings)
        menu.add_separator()
        menu.add_command(label=u'帮助', command=self.cmd_view_helpdoc)
        menu.add_separator()
        menu.add_command(label=u'退出', command=self.cmd_quit)
        self.icon_index = 1    # Set to display icon resources.1
        root.withdraw()
        self.create_ballon_tip(tip=u'感谢使用"西工大的猫"\n\n点击托盘图标可开启代理.')
        self.load_settings()
        self.INTERNET_OPTION_REFRESH = 37    # Win32 API Constants for internet_set_option
        self.INTERNET_OPTION_SETTINGS_CHANGED = 39
        root.mainloop()

    def load_settings(self):
        config = ConfigParser.ConfigParser()
        with codecs.open('NPUcat.ini', mode='r', encoding='utf-8-sig') as fp:
            config.readfp(fp)
            self.opt_proxy_override = config.get('proxy', 'proxy_override').strip()
            self.opt_address_family = config.get('proxy', 'address_family')
            self.opt_max_server_id = config.get('proxy', 'max_server_id')
            
    def flash_icon(self):
        self.stop_flash_icon = False
        while not self.stop_flash_icon:
            self.root.tk.call('winico', 'taskbar', 'modify', self.icon,
                         '-pos', self.icon_index, '-text', u'正在通过代理上网...')
            if self.icon_index == 1:
                self.icon_index = 2
            else:
                self.icon_index = 1
            time.sleep(0.5)
        self.root.tk.call('winico', 'taskbar', 'modify', self.icon,   # Stop flashing
                          '-pos', 0, '-text', u'西工大的猫 1.3')

    def callback_func(self, event, x, y):
        if event == 'WM_RBUTTONDOWN' or event == 'WM_LBUTTONDOWN':    # Right or left Click on trayicon
            self.menu.tk_popup(self.icon_pos[0] - self.menu.winfo_reqwidth(),    #pop up menu to NW side
                               self.icon_pos[1] - self.menu.winfo_reqheight())
        elif event == 'WM_MOUSEMOVE':
            self.icon_pos = int(x) - 16, int(y) - 16    # Save mouse position, later used to popup menu

    def cmd_quit(self):
        self.root.tk.call('winico', 'taskbar', 'delete', self.icon)    # Remove trayicon
        try:
            self.ballon_window.destroy()
        except:
            pass
        self.set_global_proxy('Off')    # Ensure global proxy not set
        self.root.quit()

    def create_ballon_tip(self, tip):
        try:    # Destory the last ballon window if it exists
            self.ballon_window.destroy()
        except:
            pass
        self.ballon_window = ballon_window = Toplevel(self.root)
        ballon_window.title(u'西工大的猫 1.3')
        ballon_window.resizable(False, False)
        ballon_window.attributes('-toolwindow', True)    # Set window style 
        lbl_msg = Label(ballon_window, text=tip, justify='left', fg='black')
        lbl_msg.grid(row=0,column=0, padx=20, pady=20)
        ballon_window.withdraw()    # Hide me
        ballon_window.after(1, ballon_window.update_idletasks())    # Calulate window size
        ballon_window.geometry('%sx%s+%s+%s' %
                               (ballon_window.winfo_width(), ballon_window.winfo_height(),
                                ballon_window.winfo_screenwidth() - ballon_window.winfo_width() - 16,
                                ballon_window.winfo_screenheight() - ballon_window.winfo_height() - 64 - 16
                                ))
        ballon_window.deiconify()
        self.tip_fade_in()
   
    def tip_fade_in(self):
        alpha = self.ballon_window.attributes("-alpha")
        alpha = max(alpha - 0.01, 0.3)
        self.ballon_window.attributes("-alpha", alpha)
        if alpha > 0.3:
            self.ballon_window.after(50, self.tip_fade_in)    # 0.7 / 0.01 * 50 = 3500 ms = 3.5 s
        else:
            self.ballon_window.destroy()

    def cmd_view_helpdoc(self):
        os.startfile('http://xigongda.org/help/?ver=1.3')

    def cmd_settings(self):
        os.startfile('NPUcat.ini')

    def cmd_start_proxy(self):
        if self.proxy_state.get() == 1:    # Button checked
            t = threading.Thread(target=proxy.start_proxy, args=(self,) )
            t.setDaemon(True)
            t.start()
            self.menu.entryconfig(0, label=u'代理已启用')
            self.set_global_proxy('On')
            time.sleep(0.2)    # Browser need some time to refresh proxy setttings
            os.startfile('http://www.xigongda.org/browser/thankyou/?ver=1.3')
        else:
            self.stop_flash_icon = True
            self.server.shutdown()
            self.server.socket.close()
            self.menu.entryconfig(0, label=u'启用代理')
            self.set_global_proxy('Off')
            self.server = None
            self.create_ballon_tip(tip=u'代理已停用.')

    def set_global_proxy(self, val):
        INTERNET_SETTINGS = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                           'Software\Microsoft\Windows\CurrentVersion\Internet Settings',
                                           0, winreg.KEY_ALL_ACCESS)
        if val.lower() == 'on':    # REG_DWORD = 4, REG_SZ = 1
            winreg.SetValueEx(INTERNET_SETTINGS, 'ProxyOverride', 0, 1, self.opt_proxy_override)
            winreg.SetValueEx(INTERNET_SETTINGS, 'ProxyServer', 0, 1, '127.0.0.1:1998')
            winreg.SetValueEx(INTERNET_SETTINGS, 'ProxyEnable', 0, 4, 1)
        else:
            winreg.SetValueEx(INTERNET_SETTINGS, 'ProxyEnable', 0, 4, 0)
            winreg.SetValueEx(INTERNET_SETTINGS, 'ProxyServer', 0, 1, '')
        internet_set_option = ctypes.windll.Wininet.InternetSetOptionW
        internet_set_option(0, self.INTERNET_OPTION_SETTINGS_CHANGED, 0, 0)
        internet_set_option(0, self.INTERNET_OPTION_REFRESH, 0, 0)

app = NPUcat()

