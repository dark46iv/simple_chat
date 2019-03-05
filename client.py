import argparse
import asyncio
import json
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
from sys import stdout


class Client(asyncio.Protocol):
    def __init__(self, loop, user, **kwargs):
        self.user = user
        self.is_open = False
        self.loop = loop
        self.last_message = ""

    def connection_made(self, transport):
        self.sockname = transport.get_extra_info("sockname")
        self.transport = transport
        self.transport.write(self.user.encode())
        self.is_open = True

    def connection_lost(self, exc):
        self.transport.write(f'{self.user} 0exit0'.encode())
        self.is_open = False
        self.loop.stop()

    def data_received(self, data):
        while not hasattr(self, "output"): 
            pass
        if data:
            message = json.loads(data.decode())
            self.process_message(message)

    def process_message(self, message):
        print(message)
        try:
            if message["event"] == "message":
                content = "{timestamp} | {author}: {content}".format(**message)
            elif message["event"] == "servermsg":
                content = "{timestamp} | {author} {content}".format(**message)
            elif message['event'] == 'listing_users':
                content = "{timestamp} | {author} {content}".format(**message)
                self.gui.chat_users.configure(state=tk.NORMAL)
                self.gui.users_list = message['users']
                print(self.gui.users_list)
                self.gui.chat_users.delete(1.0, 'end')
                n = 1
                for i in self.gui.users_list:
                    self.gui.chat_users.insert(f'{n}.0', i + '\n')
                    n += 1
                self.gui.chat_users.configure(state=tk.DISABLED)
            else:
                content = "{timestamp} | {author}: {content}".format(**message)

            self.output(content.strip() + '\n')
            self.gui.chat_text.see('end')
            self.gui.chat_text.configure(state=tk.DISABLED)
        except KeyError:
            print("Malformed message, skipping")

    def send(self, data):
        if data and self.user:
            self.last_message = f"{self.user}: {data}"
            self.transport.write(data.encode())


    async def getgui(self, loop):
        def executor():
            while not self.is_open:
                pass
            self.gui = Gui(None, self)
            self.output = self.tkoutput
            self.gui.chat_text.configure(state=tk.NORMAL)
            self.output("Connected to {0}:{1}\n".format(*self.sockname))
            self.gui.chat_text.configure(state=tk.DISABLED)
            self.gui.mainloop()
            self.transport.close()
            self.loop.stop()

        await loop.run_in_executor(None, executor)

    def stdoutput(self, data):
        if self.last_message.strip() == data.strip():
            return 
        else:
            stdout.write(data.strip() + '\n')

    def tkoutput(self, data):
        self.gui.chat_text.configure(state=tk.NORMAL)
        stdout.write(data)
        return self.gui.chat_text.insert('end', data)


class Gui(tk.Tk):
    """GUI для чата."""

    def __init__(self, parent, client):
        """Gui конструктор"""
        tk.Tk.__init__(self)
        self.parent = parent
        self.client = client
        self.user = client.user
        self.title('Чатик')
        self.mytext = tk.StringVar()
        self.output = self.client.tkoutput
        self.users_list = []

        self.content = tk.Frame(self)
        self.chat_text = ScrolledText(self.content)
        self.chat_users = ScrolledText(self.content, width=20)
        self.input_text = ttk.Entry(self.content, width=80, textvariable=self.mytext)
        self.enter_button = ttk.Button(self.content, text='Отправить', command=self.send)
        self.exit_button = ttk.Button(self.content, text='Выход', command=self.destroy)

        self.initialize()

    def onPressEnter(self, event):
        """При нажатии Enter срабатывала кнопка 'Отправить'"""
        self.send()


    def send(self):
        """Отправить и очистить форму отправки"""
        msg = self.mytext.get()
        self.client.send(msg)
        self.mytext.set('')

    def initialize(self):
        """Инициализация"""
        #self.users_list.append(self.user)
        self.chat_users.insert(1.0, self.user + '\n')
        self.chat_users.configure(state=tk.DISABLED)
        self.input_text.bind("<Return>", self.onPressEnter)  # как кнопка "Отправить"

        self.content.grid(column=0, row=0)
        self.chat_text.grid(column=0, row=0, padx=5)
        self.chat_users.grid(column=2, row=0, padx=5)
        self.input_text.grid(column=0, row=1)
        self.enter_button.grid(column=2, row=1, padx=5, pady=5)
        self.exit_button.grid(column=0, row=2, padx=5, pady=5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Client settings")
    parser.add_argument("--user", default="User", type=str)
    parser.add_argument("--addr", default="127.0.0.1", type=str)
    parser.add_argument("--port", default=50000, type=int)
#    parser.add_argument("--nogui", default=False, type=bool)
    args = vars(parser.parse_args())

    loop = asyncio.get_event_loop()
    userClient = Client(loop, args["user"])
    coro = loop.create_connection(lambda: userClient, args["addr"], args["port"])
    server = loop.run_until_complete(coro)

#    if args["nogui"]:
#        asyncio.ensure_future(userClient.getmsgs(loop))
#    else:
    asyncio.ensure_future(userClient.getgui(loop))

    loop.run_forever()
    loop.close()
