import pyglet

def callback(dt):
    pass
    #print(f"{1/dt:.3f} FPS")
    #print(pyglet.clock.get_fps())

pyglet.clock.schedule_interval(callback, 1/60)

def dummy_update(dt):
    pass
    #if dt != 0: print(f"{1/dt:.3f} FPS")
pyglet.clock.schedule(dummy_update)
pyglet.app.run()
