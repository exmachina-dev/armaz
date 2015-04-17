#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
import liblo as lo
from ertza.remotes.osc.server import OSCBaseServer

class ErtzaOSCServer(lo.ServerThread):
    def __init__(self, to, *args, **kwargs):
        self.to = to
        super(ErtzaOSCServer, self).__init__(*args, **kwargs)

    def reply(self, default_path, sender, *args, **kwargs):
        if kwargs and 'merge' in kwargs.keys():
            kwargs['merge'] = True
        else:
            kwargs['merge'] = False

        try:
            if type(args[0]) == str and args[0][0] == '/':
                args = list(args)
                _msg = lo.Message(args.pop(0), *args)
            elif len(args) >= 2 and kwargs['merge']:
                args = list(args)
                path = args.pop(0)
                _msg = lo.Message(default_path+'/'+path, *args)
            else:
                _msg = lo.Message(default_path, *args)
        except (TypeError, KeyError, IndexError):
            _msg = lo.Message(default_path, *args)
        self.send(sender, _msg)
        return _msg

    @lo.make_method('/status/online', 'i')
    def online_cb(self, path, args, types, sender):
        self.to.print('%s is online, listening on %s' % (
            sender.get_hostname(), args[0]))


class ErtzaActions(object):
    def __init__(self, master):
        self.master = master
        self.connected = False

        self.state = {
                'drive_enable' : False,
                }

    def load_defaults(self):
        self.master.dev_addr.set('192.168.1.12')
        self.master.dev_port.set(7900)
        self.master.srv_port.set(7901)

        self.master.ctl_drive_enable.set('Drive enable')

    def connect(self):
        self.to = {
                'dev_addr': self.master.dev_addr.get(),
                'dev_port': self.master.dev_port.get(),
                'srv_port': self.master.srv_port.get(),
                }
        if self.connected:
            del self.osc_server

        self.osc_server = ErtzaOSCServer(self, self.to['srv_port'], lo.UDP)
        self.osc_server.start()
        self.target = lo.Address(self.to['dev_addr'], self.to['dev_port'])
        self.connected = True

    def stop(self):
        pass

    def close(self):
        self.stop()
        root.destroy()

    def send(self, path, *args):
        if self.connected:
            return self.osc_server.reply(None, self.target, path, *args)

    def drive_toggle(self):
        if self.state['drive_enable']:
            self.master.ctl_drive_enable.set('Drive enable')
        else:
            self.master.ctl_drive_enable.set('Drive disable')

        self.state['drive_enable'] = not self.state['drive_enable']
        self.send('/debug/drive/driveEnable', int(self.state['drive_enable']))

        pass


class ErtzaGui(tk.Frame):
    def __init__(self, master):
        self.actions = ErtzaActions(self)
        tk.Frame.__init__(self, master)
        self.pack()
        self.create_widgets()

    def create_widgets(self):
        self.init_vars()

        self.dev_frame = tk.Frame(self)
        dv = self.dev_frame
        r = 0
        self.dev_addr_label = tk.Label(dv, text='Device address')
        self.dev_addr_label.grid(row=r, columnspan=2)
        self.dev_addr_entry = tk.Entry(dv, textvariable=self.dev_addr)
        self.dev_addr_entry.grid(row=r, column=3, columnspan=2)
        self.dev_port_label = tk.Label(dv, text=':')
        self.dev_port_label.grid(row=r, column=5, columnspan=1)
        self.dev_port_entry = tk.Entry(dv, textvariable=self.dev_port,
                width=5)
        self.dev_port_entry.grid(row=r, column=6, columnspan=1)
        r = 1
        self.srv_port_label = tk.Label(dv, text='Listen on')
        self.srv_port_label.grid(row=r, column=4, columnspan=2)
        self.srv_port_entry = tk.Entry(dv, textvariable=self.srv_port,
                width=5)
        self.srv_port_entry.grid(row=r, column=6, columnspan=1)

        self.connect_but = tk.Button(dv, text='Connect',
                command=self.actions.connect)
        self.connect_but.grid(column=4, columnspan=3)

        self.dev_frame.grid()

        self.log_frame = tk.Frame(self)
        lg = self.log_frame

        self.log_y_scroll = tk.Scrollbar(lg, orient=tk.VERTICAL)
        self.log_y_scroll.grid(row=0, column=1, sticky=tk.N+tk.S)

        self.log_x_scroll = tk.Scrollbar(lg, orient=tk.HORIZONTAL)
        self.log_x_scroll.grid(row=1, column=0, sticky=tk.E+tk.W)

        self.log_list = tk.Listbox(lg,
                xscrollcommand=self.log_x_scroll.set,
                yscrollcommand=self.log_y_scroll.set)
        self.log_list.grid(row=0, column=0,
                sticky=tk.N+tk.S+tk.E+tk.W)
        self.log_x_scroll['command'] = self.log_list.xview
        self.log_y_scroll['command'] = self.log_list.yview

        self.log_frame.grid(row=0, column=1)

        self.ctl_frame = tk.Frame(self)
        ct = self.ctl_frame

        self.ctl_enable_but = tk.Button(ct, text='Drive enable')
        self.ctl_enable_but.grid()
        self.ctl_enable_but['command'] = self.actions.drive_toggle
        self.ctl_enable_but['textvariable'] = self.ctl_drive_enable

        self.ctl_frame.grid(columnspan=2)

        self.quit_but = tk.Button(self, text="Close",
                command=self.actions.close)
        self.quit_but.grid()

    def init_vars(self):
        self.dev_addr = tk.StringVar()
        self.dev_port = tk.IntVar()
        self.srv_port = tk.IntVar()

        self.ctl_drive_enable = tk.StringVar()

        self.actions.load_defaults()


root = tk.Tk()
ertzagui = ErtzaGui(master=root)
ertzagui.master.title('Ertza GUI')
ertzagui.mainloop()
