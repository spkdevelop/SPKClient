<h3>Cliente CNC</h3>
<p>Para poder crear un nuevo taller es necesario crear un vínculo entre el servidor y la computadora que va a controlar la CNC.
Una vez establecida la conexión, podrás subir tus propios archivos a la nube, ya sea manualmente o utilizando nuestro plugin de Rhino5 <a href="http://www.spkautomatizacion.com/item/ivdT28PCa" style="color:blue">SPKCAM</a>.</p>
<p>Necesitas tener una CNC con sistema de control 
<a href="https://github.com/synthetos/TinyG" style="color:blue">TinyG</a> o <a href="https://github.com/grbl/grbl" style="color:blue">GRBL</a>.
Todas nuestras CNCs pre ensambladas tienen este sistema de control es popular entre 
muchas otras marcas como <a href="https://www.shapeoko.com" style="color:blue">Shapeoko</a> y <a href="https://www.inventables.com/technologies/x-carve" style="color:blue">XCarve</a>.</p>
<p>El cliente está diseñado para funcionar en una RaspberryPi, sin embargo, puede correr en cualquier computadora con sistema operativo linux.
Te recomenadamos comprar una <a href="https://github.com/grbl/grbl" style="color:blue">RaspberryPi</a> con nuestro cliente previamente instalado o seguir las siguientes instrucciones para hacerlo tú mismo.</p> 
<h3>Descarga e instala el cliente en <a href="http://www.ubuntu.com/download/desktop" style="color:blue">Ubuntu</a> o <a href="https://www.raspberrypi.org/downloads/raspbian/" style="color:blue">Raspbian</a></h3>
<p>Estas instrucciones suponen que ya cuentas con un sistema operativo linux Ubuntu. Todavía tenemos que instalar dos dependecias previas a correr el script: xvfb-run y python-spynner. Revisa nuestra proyecto en <a href="https://github.com/utitankaspk/SPKClient" style="color:blue">GitHub</a> para más información.</p>

Descarga el ZIP <a href="https://github.com/utitankaspk/SPKClient/archive/master.zip" style="color:blue">SPKClient-master.zip</a>.<br>
	Crea una nueva carpeta en el escritorio llamada SPKClient-master.<br>
	Descomprime el ZIP en la carpeta.<br>
	<span style="margin:50px;color:rgb(50,50,50);">Debe contener los archivos main.py, start.py ,cutter.py en primer nivel.</span> <br>
	Abre una terminal. Después copia y pega sin comillas los siguientes comandos:<br><br>

  <i>"sudo apt-get build-dep -y libqt4-dev"<br></i>
	<i>"sudo apt-get install -y python-qt4"<br></i>
	<i>"sudo apt-get install -y libxtst-dev xvfb x11-xkb-utils"</i><br>
	<i>"sudo apt-get install -y python-dev python-setuptools python-pip"</i><br>
	<i>"sudo pip install spynner"</i><br>

Ve a la carpeta donde colocaste los archivos de SPKClient y ejecuta el script con el identificador de usuario y máquina.<br><br>
	<i>"cd /home/tuusuarioaqui/Desktop/CNC" </i><br><br>
	<span style="color:rgb(50,50,50)"> También puedes escribir <i>"cd" </i> y arrastra la carpeta de SPKClient a la terminal.</span><br>
	Llena el formato de Nueva CNC al inicio de la página y copia y pega el código generado en tu terminal.<br><br>
	Ejemplo:<br><br>
    <small><i>sudo xvfb-run python main.py "JTdCJTIyZW1haWwlMjI6JTIyZGFuaWVsQHNwa2F1d<br>
    G9tYXRpemFjaW9uLmNvbSUyMiwlMjJ3b3Jrc2hvcF9pZCUyMjolMjJhZ3B6Zm5Od2EyTnNiM1ZrY2hVTE<br>
    VnaFhiM0pyYzJodmNCaUFnSUNBd0t1R0NndyUyMiwlMjJuZXdfd29ya3Nob3BfbmFtZSUyMjolMjIlMjI<br>
    sJTIyY25jX25hbWUlMjI6JTIyZGFuaWVsJTIyJTdE"<br><br>
	</i></small>
	El script se debe ejecutar con el comando <i>"sudo xvfb-run python main.py"</i> y el código de usuario que identifica el cliente con el usuario dentro del servidor. Éste sólo se necesita la primera vez que se ejecuta el script.<br>
	<br></li>
	</div>
<p>Si el script se ejecutó con éxito, aparecerá el nombre del taller que acabas de crear en el menú de talleres, en la barra superior. Si el script del cliente se ejecutó correctamente y no aparece en la barra, reinicia la página.
Si tienes problemas, no dudes en contactarnos.</p>
<a href="mailto:daniel@spkautomatizacion.com?Subject=SPK Client" target="_top" style="color:blue">Programación SPK:.</a>
	
	
	
</div>
</div>
