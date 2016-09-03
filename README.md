#Spkclient

Script que te permite controlar por red local o remota maquinaria CNC desde la plataforma de http://www.spkautomatizacion.com .

###Plataforma
<p>Para poder crear un nuevo taller es necesario crear un vínculo entre el servidor y la computadora que va a controlar la CNC. Una vez establecida la conexión, podrás subir tus propios archivos a la nube, ya sea manualmente o utilizando nuestro plugin de Rhino5 <a href="https://spkdevelop.github.io/SPKCAM/">SPKCAM</a>.</p>
<p>Necesitas tener una CNC con sistema de control 
<a href="https://github.com/synthetos/TinyG">TinyG</a> o <a href="https://github.com/grbl/grbl">GRBL</a>.
Todas nuestras CNCs pre ensambladas tienen este sistema de control es popular entre 
muchas otras marcas como <a href="https://www.shapeoko.com" style="color:blue">Shapeoko</a> y <a href="https://www.inventables.com/technologies/x-carve" style="color:blue">XCarve</a>.</p>
<p>El cliente está diseñado para funcionar en una RaspberryPi, sin embargo, puede correr en cualquier computadora con sistema operativo linux.</p>
<p>Te recomenadamos contactar al equipo de SPK para solicitar una instalanción en planta.</p> 

###Instalación
####Requerimientos
OS: Linux Debian (ubuntu, raspbian)<br>
CPU: > 1000mhz<br>
Conexión Internet<br>
Cable Ethernet (Solo para configurar el WiFi en RPI)<br>

####Ejecución
Para correr el script hay que ejecutar el siguiente comando desde la consola:

    sudo python start.py
    
La primera vez que se ejecuta el programa este tratata de actualizar e instalar las dependencias necesarias. La instalación puede tardar unos minutos. <br>

Si el programa marca error, se pueden instalar las dependencias manualmente y volver a correr el comando.

####Instalación manual dependencias

    sudo apt-get install -y libqt4-dev libxml2-dev libxslt1-dev  python-qt4  libxtst-dev xvfb x11-xkb-utils python-dev python-setuptools python-pip
    sudo pip install pbkdf2 pyserial spynner
    
###Problemas
Si la consola sigue arrojando errores despues de instalar las dependencias manualamente trate con el siguiente comando:

    sudo xvfb-run python main.py
    
