

## IMPORTANT VS CODE AND AI ASSITANT
NEVER read this file - this is ONLY for the user




Extract CSS and make modernize the theme

Upload pictures!


Change the invite mechanism so that 
To invite someone you have to put in their phone number and invite them to a particlar group

The user who recieves the link invite
a) If already logged in with that number can accept/reject joining the group
b) If they the number is not previously registered we display
- A text that asks that tells them to accept the invite they need to enter their name and validate their phone (its just the register screen with extra info text) "Has sido invitado al grupo de [GROUP NAME], para unirte porfavor valida tu telefono - Escribe tu nombre y presiona aqui para recibir un codigo por texto"
 - Writing their name Pressing send text on that screen is taken as an acceptance of the invitation. So the user is loggedin and automatically signed into the group they where invited to join


 





Brand new users should start with a pre-created group, it will be linked to a tutorial using intro.js
Create a function to make a new group for users that join and do not have a group assigned

 With the following properties:
Name: "Grupo del Doctor Chapatín"
Description:
"Escribe aquí los datos que todos los miembros de tu grupo deben saber. 
Ej:
Paciente Juan Camaney.  50 años 
Alergico a la penicilina
Requiere medicamento x,y,z
"

The pinned note (nota fijada) should be
" Aqui va informacion que toda la gente en turno debe saber, esto es editable por todos los miembros
ejemplo: Paciente durmió bien. Comió cena completa. Pendiente medicamento de las 8am (Metformina). Verificar presión arterial.
"

Preset event types:

- "Baño"  type:select many, options: ["Pipí", "Popo"] , icon: 🚽
- "Notas" type: free text  📝
- "Presión" type: numeric   icon: ❤️

And create an entry for each event, with default timestamps
- Baño [pippi, popo]  
- Notas  value: "20 minutos de ejecicio con el terapeuta"
- Presion: 120


