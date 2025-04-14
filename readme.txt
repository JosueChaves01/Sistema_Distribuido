para instalar react

# Download and install fnm:
winget install Schniz.fnm

luego se reinicia la terminal, y se ejecuta

# Download and install Node.js:
fnm install 22

para verificar instalacion

# Verify the Node.js version:
node -v # Should print "v22.14.0".

# Verify npm version(evitar la terminal de powershell):
npm -v # Should print "10.9.2".


para instalar RabbitMQ

# Descargar Erlang desde:
https://www.erlang.org/downloads

# Descargar RabbitMQ desde:
https://www.rabbitmq.com/install-windows.html

# Abre el símbolo del sistema (CMD) como administrador y ejecuta:
rabbitmq-plugins enable rabbitmq_management

rabbitmq-service start
