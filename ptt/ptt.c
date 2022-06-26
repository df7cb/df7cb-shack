/*
 * Turn on PTT using hamlib when some key is pressed in X11.
 */

#include <hamlib/rig.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <X11/XKBlib.h> // XkbSetDetectableAutoRepeat
#include <X11/Xlib.h>
#include <X11/Xutil.h>

#define PTT_KEY XK_F30
#define MY_RIG RIG_MODEL_NETRIGCTL

RIG *
open_rig()
{
    int retcode;        /* generic return code from functions */

    rig_model_t myrig_model = MY_RIG;
    rig_set_debug_level(RIG_DEBUG_NONE);

    RIG *my_rig = rig_init(myrig_model);
    if (!my_rig)
    {
        fprintf(stderr, "Unknown rig num: %d\n", myrig_model);
        fprintf(stderr, "Please check riglist.h\n");
        exit(1); /* whoops! something went wrong (mem alloc?) */
    }

    retcode = rig_open(my_rig);
    if (retcode != RIG_OK)
    {
        printf("rig_open: error = %s\n", rigerror(retcode));
        exit(2);
    }
    return my_rig;
}

int
set_ptt(RIG *my_rig, int ptt)
{
    int retcode;        /* generic return code from functions */

    retcode = rig_set_ptt(my_rig, RIG_VFO_A, ptt);  /* stand back ! */
    if (retcode != RIG_OK)
    {
        printf("rig_set_ptt: error = %s \n", rigerror(retcode));
    }
    return 0;
}

Display *
setup_x()
{
    Display*    dpy     = XOpenDisplay(0);
    Window      root    = DefaultRootWindow(dpy);

    Bool            supports_detectable_autorepeat;
    XkbSetDetectableAutoRepeat(dpy, true, &supports_detectable_autorepeat);

    unsigned int    modifiers       = AnyModifier;
    int             keycode         = XKeysymToKeycode(dpy, PTT_KEY);
    Window          grab_window     = root;
    Bool            owner_events    = False;
    int             pointer_mode    = GrabModeAsync;
    int             keyboard_mode   = GrabModeAsync;

    XGrabKey(dpy, keycode, modifiers, grab_window, owner_events, pointer_mode,
             keyboard_mode);

    //XSelectInput(dpy, root, KeyPressMask);

    return dpy;
}

void loop(RIG *my_rig, Display *dpy)
{
    XEvent      ev;
    char keys[32];
    int             keycode         = XKeysymToKeycode(dpy, PTT_KEY);
    Bool ptt_is_on = false;

    while(true)
    {
        XNextEvent(dpy, &ev);
        XQueryKeymap(dpy, keys);
        Bool is_pressed = keys[keycode>>3] & (1<<(keycode&7));

        if (is_pressed != ptt_is_on) {
            //printf("Action\n");
            set_ptt(my_rig, is_pressed ? RIG_PTT_ON : RIG_PTT_OFF);
            ptt_is_on = is_pressed;
        }
    }
}

int main()
{
    RIG *my_rig = open_rig();
    set_ptt(my_rig, RIG_PTT_OFF);
    Display *dpy = setup_x();

    loop(my_rig, dpy);

    XCloseDisplay(dpy);
    return 0;
}
