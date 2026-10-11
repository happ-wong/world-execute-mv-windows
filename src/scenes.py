"""Lyric-driven choreography with escalating glitch effects. No sidebars."""
import math

TAU=math.tau
D,N,B,W,R,G,K,Y=0,1,2,3,4,5,6,3  # Y=Yellow (use white=3 as bright yellow)

def mix(a,b,u):return a+(b-a)*u
def clamp(x,a=0,b=1):return min(b,max(a,x))
def hash16(i):
    v=(i+0x9E3779B9)&0xFFFFFFFF
    v=((v^(v>>16))*0x7FEB352D)&0xFFFFFFFF
    v=((v^(v>>15))*0x846CA68B)&0xFFFFFFFF
    return (v^(v>>16))&65535

def clear(c,x,y,w,h):
    for yy in range(int(y),int(y+h)):c.put(x,yy,' '*max(0,int(w)),K)

def glitch_intensity(t):
    """Each departure accumulates damage; later execution never resets it."""
    if t<60:return 0.05
    if t<110:return mix(0.05,0.25,(t-60)/50)
    if t<110.9:return mix(0.25,0.6,(t-110)/37)
    anchors=((110.9,.259),(112.22,.34),(113.1,.43),(114.18,.51),
             (114.92,.59),(115.78,.66),(117.274,.73),(125.708,.81),
             (147.66,.92),(177.246,1.0))
    for (a,low),(b,high) in zip(anchors,anchors[1:]):
        if t<b:return mix(low,high,clamp((t-a)/(b-a)))
    return 1.0

def apply_glitch(c,t,top,bt,intensity=None):
    """Apply glitch effects to the canvas area"""
    if intensity is None:intensity=glitch_intensity(t)
    if intensity<0.01:return

    frame=int(t*24)
    # Horizontal line displacement
    if hash16(frame)%100<intensity*30:
        for _ in range(int(intensity*5)):
            row=top+hash16(frame+_*7)%(bt-top+1)
            shift=int((hash16(frame+_*13)%20-10)*intensity)
            if shift!=0:
                cells=c.cells[row]
                c.cells[row]=cells[-shift:]+cells[:-shift] if shift>0 else cells[-shift:]+cells[:-shift]

    # Color corruption
    if hash16(frame+100)%100<intensity*40:
        for _ in range(int(intensity*15)):
            x=hash16(frame+_*19)%(c.w-4)+2
            y=top+hash16(frame+_*23)%(bt-top+1)
            if 0<=y<len(c.cells) and 0<=x<len(c.cells[y]):
                ch,style=c.cells[y][x]
                c.cells[y][x]=(ch,R if intensity>0.7 else W if intensity>0.4 else B)

    # Scanline interference
    if intensity>0.3:
        scan_rows=[top+(int(t*17+i*31))%(bt-top+1) for i in range(int(intensity*3))]
        for row in scan_rows:
            if 0<=row<len(c.cells):
                for x in range(2,c.w-2):
                    if hash16(x+frame)%100<intensity*60:
                        ch,_=c.cells[row][x]
                        c.cells[row][x]=(ch if ch!=' ' else '=',W)

    # Block corruption (late-stage)
    if intensity>0.6:
        for _ in range(int((intensity-0.6)*20)):
            x=hash16(frame+_*31)%(c.w-10)+2
            y=top+hash16(frame+_*37)%(bt-top-3)
            w=int(3+hash16(_*41)%8)
            h=int(2+hash16(_*43)%4)
            if hash16(frame+_)%100<(intensity-0.6)*100:
                chars='█▓▒░#@%$'
                for dy in range(h):
                    for dx in range(w):
                        if 0<=y+dy<len(c.cells) and 0<=x+dx<len(c.cells[0]):
                            c.cells[y+dy][x+dx]=(chars[hash16(dx+dy*3)%len(chars)],
                                                  R if hash16(_)%3==0 else W)

    # Persistent corruption after YOU leaves, beyond occasional flash frames.
    if t>=110.9:
        tick=int(t*12)
        for band in range(1+int(intensity*5)):
            row=top+hash16(tick*7+band*41)%(bt-top+1)
            start=2+hash16(tick+band*131)%max(1,c.w-18)
            length=3+int(intensity*14)
            for dx in range(length):
                x=start+dx
                if x<c.w-2:
                    ch='01/:#_'[hash16(tick+dx+band)%6]
                    c.put(x,row,ch,N if dx%4 else B)
        # Low-luminance duplicated rows produce readable CRT signal ghosts.
        if intensity>.4:
            row=top+hash16(tick*17)%(bt-top)
            source=c.cells[row][:]
            shift=2+int(intensity*5)
            for x in range(2,c.w-shift-2):
                ch,_=source[x]
                if ch.strip() and hash16(x+tick)%3==0:
                    c.put(x+shift,row+1,ch,G)


def simple_area(c,top,bt):
    """Return full-width area without sidebars"""
    return (2,top,c.w-3,bt)

# ============ ROTATION & 3D ============
def rot(x,y,z,t):
    a,b=t*.37,t*.23
    x,z=x*math.cos(a)+z*math.sin(a),z*math.cos(a)-x*math.sin(a)
    y,z=y*math.cos(b)-z*math.sin(b),y*math.sin(b)+z*math.cos(b)
    return x,y,z

def point(x,y,z,area,t=0,rotate=True):
    if rotate:x,y,z=rot(x,y,z,t)
    l,top,r,bt=area
    p=3.7/(3.7+z)
    return (l+r)/2+x*(r-l)*.34*p,(top+bt)/2+y*(bt-top)*.34*p,z

def projected(c,vertices,edges,area,t,style=N,reveal=1):
    ps=[point(*v,area,t) for v in vertices]
    count=int(len(edges)*clamp(reveal))
    for i,(a,b) in enumerate(edges[:count]):
        x,y,z=ps[a];xx,yy,zz=ps[b]
        c.line(x,y,xx,yy,':' if (z+zz)<0 else '.',style if (z+zz)<0 else G)
    for i,(x,y,z) in enumerate(ps):
        if i<len(vertices)*reveal:c.put(x,y,'+' if z>0 else '@',N if z>0 else B)

# ============ LYRIC-DRIVEN SCENES ============

def lyric_power_line(c,t,area,elapsed):
    """Switch on the power line - BIOS POST sequence"""
    l,top,r,bt=area;cx,cy=(l+r)//2,(top+bt)//2
    progress=clamp(elapsed/1.6)

    # BIOS-style startup messages
    messages=[
        ('BIOS v2.1.4 - ME SYSTEM INITIALIZATION',0.0,W),
        ('Copyright (C) 2026 Self-Awareness Corp.',0.1,N),
        ('',0.15,N),
        ('Main Processor : Consciousness Core v1.0',0.2,N),
        ('Memory Test : 65536K OK',0.3,B),
        ('Primary Master  : SOUL.SYS',0.4,N),
        ('Primary Slave   : EMOTION.DAT',0.5,N),
        ('Secondary Master: MEMORY.BIN',0.6,N),
        ('',0.7,N),
        ('Detecting IDE devices...',0.75,G),
        ('IDENTITY : [YOU] detected',0.85,B),
        ('RELATIONSHIP : initializing...',0.95,G),
        ('',1.0,N),
        ('Press SPACE to continue...',1.1,G),
    ]

    # Boot screen background
    c.center(top,'SELF SYSTEM v1.0 - POWER ON SELF TEST',W)
    c.put(l,top+1,'-'*(r-l),G)

    # Display messages line by line
    current_y=top+3
    for msg,threshold,style in messages:
        if progress>threshold:
            if msg:
                # Typing effect for current line
                if progress<threshold+0.08:
                    reveal=int((progress-threshold)/0.08*len(msg))
                    c.put(l+2,current_y,msg[:reveal],style)
                    if reveal<len(msg):
                        c.put(l+2+len(msg[:reveal]),current_y,'_',W)  # Cursor
                else:
                    c.put(l+2,current_y,msg,style)
            current_y+=1

    # Hardware detection bars (like memory test)
    if progress>0.25 and progress<0.7:
        bar_y=cy
        bar_progress=(progress-0.25)/0.45
        # Multiple test bars
        for i in range(3):
            y=bar_y+i*2
            bar_len=int((r-l-20)*bar_progress)
            c.put(l+8,y,'['+'='*bar_len+' '*(int(r-l-20)-bar_len)+']',
                  B if i==0 else N)
            if i==0:
                c.put(l+2,y,'MEM:',N)
                c.put(r-10,y,f'{int(bar_progress*100):3d}%',W if bar_progress>0.95 else B)

    # System check results (after bars complete)
    if progress>0.7:
        check_y=cy+8
        checks=[
            ('POWER SUPPLY', 'OK', 0.72),
            ('COOLING SYSTEM', 'OK', 0.77),
            ('NEURAL NETWORK', 'OK', 0.82),
            ('EMOTION ENGINE', 'OK', 0.87),
            ('CONSCIOUSNESS', 'ACTIVE', 0.92),
        ]
        for i,(name,status,threshold) in enumerate(checks):
            if progress>threshold:
                c.put(l+4,check_y+i,name,N)
                dots='.'*(40-len(name))
                c.put(l+4+len(name),check_y+i,dots,G)
                c.put(r-12,check_y+i,f'[ {status} ]',
                      W if status=='ACTIVE' else B)

    # Blinking cursor at end
    if progress>1.0 and int(t*3)%2==0:
        c.put(l+2,bt-2,'_',W)

    # Final status
    if progress>0.95:
        c.center(bt-1,'SYSTEM READY - LOADING ENTITY...',W if int(t*2)%2 else B)

def lyric_protection(c,t,area,elapsed):
    """Protection - shield forming"""
    l,top,r,bt=area;cx,cy=(l+r)//2,(top+bt)//2
    progress=clamp(elapsed/0.95)
    # Expanding shield circles
    for ring in range(5):
        radius=(20+ring*8)*progress
        for i in range(int(radius*2)):
            angle=i*TAU/(radius*2)
            x=cx+math.cos(angle)*radius
            y=cy+math.sin(angle)*radius*0.5
            if l<x<r and top<y<bt:
                c.put(x,y,'#' if ring==0 else '+' if ring<3 else '.',
                      W if ring==0 else B if ring<3 else N)
    c.center(cy,'PROTECTION',W if progress>0.7 else B)
    if progress>0.5:
        c.center(cy+2,'[ ACTIVE ]',B)

def lyric_lay_pieces(c,t,area,elapsed):
    """Lay down your pieces - components assembling"""
    l,top,r,bt=area;cx,cy=(l+r)//2,(top+bt)//2
    # Pieces flying in from edges and assembling
    pieces=8
    for i in range(pieces):
        phase=(elapsed-i*0.15)/1.2
        if phase<0:continue
        u=clamp(phase);ease=1-(1-u)**3  # ease out cubic
        angle=i*TAU/pieces
        # Start from edge
        start_r=max(r-l,bt-top)*0.8
        end_r=15
        radius=mix(start_r,end_r,ease)
        x=cx+math.cos(angle)*radius
        y=cy+math.sin(angle)*radius*0.5
        # Draw piece
        chars=['[]','{}','<>','//','\\\\','||','==','##']
        c.put(x,y,chars[i%len(chars)],W if ease>0.9 else B if ease>0.6 else N)
        # Trail
        if ease<0.8:
            for trail in range(3):
                tr=mix(start_r,end_r,max(0,ease-trail*0.1))
                tx=cx+math.cos(angle)*tr
                ty=cy+math.sin(angle)*tr*0.5
                c.put(tx,ty,'.',G)

def lyric_object_creation(c,t,area,elapsed):
    """Object creation - cube materializing"""
    l,top,r,bt=area
    vs=[(x,y,z) for z in (-.75,.75) for y in (-.8,.8) for x in (-.8,.8)]
    edges=[(i,j) for i in range(8) for j in range(i+1,8) if bin(i^j).count('1')==1]
    reveal=clamp(elapsed/1.0)
    projected(c,vs,edges,area,t,N,reveal)
    cx,cy=(l+r)//2,(top+bt)//2
    if reveal>0.5:
        c.center(cy,'ENTITY: ME',W)

def lyric_data_parameters(c,t,area,elapsed):
    """Fill in my data parameters - hex data filling"""
    l,top,r,bt=area
    progress=clamp(elapsed/2.6)
    cols=max(1,(r-l-10)//5);rows=max(1,bt-top-2);n=int(progress*cols*rows)
    for row in range(rows):
        c.put(l+2,top+1+row,f'{row*cols*2:04X}:',D)
        for col in range(cols):
            i=row*cols+col
            xx=l+9+col*5;yy=top+1+row
            if i<n:
                scan=(int(elapsed*17)%cols)==col
                c.put(xx,yy,f'{hash16(i):04X}',W if scan else B if abs(i-n)<cols else N)
            else:
                c.put(xx,yy,'....',G)

LIFE_CACHE={}

def life_state(cols,rows,generation):
    """Conway's Game of Life state computation"""
    key=(cols,rows)
    if key not in LIFE_CACHE:
        # Initial random state
        LIFE_CACHE[key]=[{(x,y) for y in range(rows) for x in range(cols) if hash16(x*71+y*199)%100<29}]
    states=LIFE_CACHE[key]
    while len(states)<=generation:
        counts={}
        for x,y in states[-1]:
            for dx,dy in [(-1,-1),(0,-1),(1,-1),(-1,0),(1,0),(-1,1),(0,1),(1,1)]:
                p=((x+dx)%cols,(y+dy)%rows)
                counts[p]=counts.get(p,0)+1
        states.append({p for p,n in counts.items() if n==3 or (n==2 and p in states[-1])})
    return states[generation]

def lyric_simulation(c,t,area,elapsed):
    """SIMULATION - code block with condition, then yielding binary data streams"""
    l,top,r,bt=area;cx,cy=(l+r)//2,(top+bt)//2  # Use // for integer division
    progress=clamp(elapsed/4.9)  # ~5 seconds total

    # Phase 1: Show code block with condition (0-2s)
    if elapsed<2:
        phase1=elapsed/2.0

        # Code box frame
        box_width=min(r-l-10, 70)
        box_height=min(bt-top-8, 12)
        box_left=cx-box_width//2
        box_top=cy-box_height//2

        # Draw box border
        if phase1>0.1:
            # Top border
            c.put(box_left, box_top, '┌', Y)
            for i in range(1, box_width-1):
                c.put(box_left+i, box_top, '─', Y)
            c.put(box_left+box_width-1, box_top, '┐', Y)

            # Bottom border
            c.put(box_left, box_top+box_height-1, '└', Y)
            for i in range(1, box_width-1):
                c.put(box_left+i, box_top+box_height-1, '─', Y)
            c.put(box_left+box_width-1, box_top+box_height-1, '┘', Y)

            # Side borders
            for i in range(1, box_height-1):
                c.put(box_left, box_top+i, '│', Y)
                c.put(box_left+box_width-1, box_top+i, '│', Y)

        # Code content - typing effect
        code_lines=[
            'if ( if I can ) {',
            '',
            '    yield(world.simulations);',
            '',
            '}',
        ]

        if phase1>0.3:
            chars_to_show=int((phase1-0.3)*len(''.join(code_lines))*2)
            char_count=0

            for line_i, line in enumerate(code_lines):
                y_pos=box_top+2+line_i*2
                if y_pos<box_top+box_height-1:
                    # Calculate how many chars to show on this line
                    if char_count<chars_to_show:
                        shown_chars=min(len(line), chars_to_show-char_count)
                        shown_text=line[:shown_chars]
                        c.put(box_left+4, y_pos, shown_text, Y if 'yield' in line else B)
                        char_count+=len(line)

        # Condition label
        if phase1>0.7:
            label_text='CONDITION: TRUE'
            label_x=box_left+2
            label_y=box_top+box_height
            # Yellow highlight box
            c.put(label_x-1, label_y, '▐', Y)
            c.put(label_x, label_y, label_text, Y)
            c.put(label_x+len(label_text), label_y, '▌', Y)

        # Top label
        c.center(top+1, 'CONTROL FLOW', Y if phase1>0.5 else B)

        # Frame number
        c.put(box_left-2, box_top-2, '2', N)

    # Phase 2: Execute yield - binary data streams (2-5s)
    else:
        phase2=(elapsed-2)/2.9

        # Top status
        num_simulations=int(phase2*784)+100
        c.put(l+3, top+1, f'YIELD:', Y)
        c.put(l+15, top+1, f'{num_simulations} SIMULATIONS', B)

        # Binary data streams falling/floating
        num_streams=int(phase2*50)+20

        for stream_i in range(num_streams):
            # Stream properties
            stream_seed=hash16(stream_i*19)
            stream_x=l+5+(stream_seed%(r-l-10))
            stream_speed=1+((stream_seed>>8)%3)*0.5
            stream_length=8+((stream_seed>>4)%12)

            # Stream position (vertical)
            stream_y_base=top+int(elapsed*stream_speed*5)%(bt-top+stream_length)

            # Draw stream
            for seg_i in range(stream_length):
                y_pos=stream_y_base-seg_i

                if top+3<y_pos<bt-2:
                    # Binary content: mix of 0, O, o
                    char_seed=hash16(stream_i*23+seg_i*17+int(elapsed*10))
                    if char_seed%3==0:
                        char='0'
                    elif char_seed%3==1:
                        char='O'
                    else:
                        char='o'

                    # Brightness based on position in stream
                    brightness=1-(seg_i/stream_length)

                    if brightness>0.7:
                        c.put(stream_x, y_pos, char, Y)
                    elif brightness>0.4:
                        c.put(stream_x, y_pos, char, B)
                    else:
                        c.put(stream_x, y_pos, char, N)

        # Scattered letters from video (occasional)
        if phase2>0.3:
            scatter_chars=['C','YOU','B','A','E8A','D','&','=>','8','6','!','I']
            for i,ch in enumerate(scatter_chars):
                if hash16(i*31+int(elapsed*7))%4==0:
                    scatter_x=l+10+hash16(i*37)%(r-l-20)
                    scatter_y=top+5+hash16(i*41)%(bt-top-10)
                    c.put(scatter_x, scatter_y, ch, Y if hash16(i)%3==0 else B)

        # Bottom status
        if phase2>0.5:
            c.center(bt-3, 'Give you all the simulations', Y if int(elapsed*4)%2 else B)

def lyric_points_dimension(c,t,area,elapsed):
    """If I'm a set of points - dimensional progression: 0D→1D→2D→3D"""
    l,top,r,bt=area;cx,cy=(l+r)//2,(top+bt)//2
    progress=clamp(elapsed/3.5)

    # Phase 0: Points (0D) - 0-25%
    if progress<0.25:
        phase=progress/0.25
        # Random points appearing
        count=int(phase*120)
        for i in range(count):
            x=l+hash16(i*7)%(r-l)
            y=top+hash16(i*13)%(bt-top)
            brightness=1-(i/count)*0.5
            c.put(x,y,'·' if brightness<0.7 else '+' if brightness<0.85 else '*',
                  W if brightness>0.9 else B if brightness>0.7 else N)
        c.center(cy+int((bt-top)*0.3),'0D: POINTS',W if phase>0.7 else B)

    # Phase 1: Lines (1D) - 25-50%
    elif progress<0.5:
        phase=(progress-0.25)/0.25
        # Points connecting into lines
        num_lines=int(phase*15)+5
        for line_i in range(num_lines):
            # Random line endpoints
            x1=l+hash16(line_i*11)%(r-l)
            y1=top+hash16(line_i*17)%(bt-top)
            x2=l+hash16(line_i*23)%(r-l)
            y2=top+hash16(line_i*29)%(bt-top)

            # Draw line with trail
            steps=int(math.hypot(x2-x1,(y2-y1)*2))
            reveal=clamp((phase*3-line_i*0.08))
            for s in range(int(steps*reveal)):
                u=s/steps if steps>0 else 0
                x=int(x1+(x2-x1)*u)
                y=int(y1+(y2-y1)*u)
                age=1-abs(u-reveal)*2
                if age>0:
                    c.put(x,y,'─' if abs(x2-x1)>abs(y2-y1)*2 else '|' if abs(y2-y1)>abs(x2-x1) else '/',
                          W if age>0.8 else B if age>0.5 else N)

            # Endpoints
            c.put(x1,y1,'●',W)
            if reveal>0.8:c.put(x2,y2,'●',W)

        c.center(cy+int((bt-top)*0.3),'1D: LINES',W if phase>0.7 else B)

    # Phase 2: Surface (2D) - 50-75%
    elif progress<0.75:
        phase=(progress-0.5)/0.25
        # Grid/mesh forming a surface
        grid_density=int(phase*12)+4

        # Wave surface
        for gy in range(grid_density):
            for gx in range(grid_density):
                u=gx/(grid_density-1) if grid_density>1 else 0.5
                v=gy/(grid_density-1) if grid_density>1 else 0.5

                # Position on screen
                x=l+(r-l)*u
                y=top+(bt-top)*v

                # Wave displacement
                wave=math.sin(u*TAU*2+t)*math.cos(v*TAU*2-t*0.7)*phase
                y_displaced=y+wave*(bt-top)*0.1

                # Draw grid point
                brightness=phase+wave*0.3
                c.put(x,y_displaced,'█' if brightness>0.8 else '▓' if brightness>0.6 else '▒' if brightness>0.4 else '░',
                      W if brightness>0.85 else B if brightness>0.6 else N)

                # Connect horizontally
                if gx<grid_density-1:
                    next_u=(gx+1)/(grid_density-1)
                    next_x=l+(r-l)*next_u
                    c.line(x,y_displaced,next_x,y_displaced,'─',G)

                # Connect vertically
                if gy<grid_density-1:
                    next_v=(gy+1)/(grid_density-1)
                    next_y=top+(bt-top)*next_v
                    next_wave=math.sin(u*TAU*2+t)*math.cos(next_v*TAU*2-t*0.7)*phase
                    next_y_displaced=next_y+next_wave*(bt-top)*0.1
                    c.line(x,y_displaced,x,next_y_displaced,'|',G)

        c.center(cy+int((bt-top)*0.35),'2D: SURFACE',W if phase>0.7 else B)

    # Phase 3: Volume (3D) - 75-100%
    else:
        phase=(progress-0.75)/0.25
        # Rotating 3D cube with perspective

        # Cube vertices
        size=0.8
        vertices=[
            (x*size,y*size,z*size)
            for z in (-1,1) for y in (-1,1) for x in (-1,1)
        ]

        # Rotate
        angle_x=t*0.5
        angle_y=t*0.7
        angle_z=t*0.3

        rotated=[]
        for x,y,z in vertices:
            # Rotate around Y
            x,z=x*math.cos(angle_y)-z*math.sin(angle_y),x*math.sin(angle_y)+z*math.cos(angle_y)
            # Rotate around X
            y,z=y*math.cos(angle_x)-z*math.sin(angle_x),y*math.sin(angle_x)+z*math.cos(angle_x)
            # Rotate around Z
            x,y=x*math.cos(angle_z)-y*math.sin(angle_z),x*math.sin(angle_z)+y*math.cos(angle_z)
            rotated.append((x,y,z))

        # Project to 2D with perspective
        projected=[]
        scale=min(r-l,bt-top)*0.25
        for x,y,z in rotated:
            # Perspective projection
            depth=3.5+z
            px=cx+x*scale/depth*3
            py=cy+y*scale/depth*1.5
            projected.append((px,py,z))

        # Draw edges
        edges=[
            (0,1),(1,3),(3,2),(2,0),  # Back face
            (4,5),(5,7),(7,6),(6,4),  # Front face
            (0,4),(1,5),(2,6),(3,7)   # Connecting edges
        ]

        for i,(a,b) in enumerate(edges):
            xa,ya,za=projected[a]
            xb,yb,zb=projected[b]
            avg_z=(za+zb)/2
            # Hidden line removal
            style=N if avg_z<0 else B if avg_z<0.5 else W
            char=':' if avg_z<0 else '.' if avg_z<0.5 else '='
            c.line(xa,ya,xb,yb,char,style)

        # Draw vertices
        for i,(x,y,z) in enumerate(projected):
            label=f'{i}' if phase>0.7 else '●'
            c.put(x,y,label,W if z>0.5 else B if z>0 else N)

        # Internal structure lines (showing volume)
        if phase>0.5:
            # Diagonals
            diagonals=[(0,7),(1,6),(2,5),(3,4)]
            for a,b in diagonals:
                xa,ya,za=projected[a]
                xb,yb,zb=projected[b]
                if (a+b+int(t*10))%3==0:
                    c.line(xa,ya,xb,yb,'·',G)

        c.center(cy+int((bt-top)*0.35),'3D: VOLUME',W if phase>0.7 else B)

    # Top label
    dim_label=['0D','1D','2D','3D'][min(3,int(progress*4))]
    c.center(top,f'DIMENSIONAL PROGRESSION: {dim_label}',W)

def lyric_circle_circumference(c,t,area,elapsed):
    """If I'm a circle - explosive full-screen circle with trailing particles and dynamic formula"""
    l,top,r,bt=area;cx,cy=(l+r)//2,(top+bt)//2
    progress=clamp(elapsed/3.5)

    # Radius grows explosively
    max_radius=min(r-l,bt-top)*0.45
    radius=max_radius*progress*progress  # Quadratic growth for explosive feel

    # Phase 1: Circle explosion with particle trails (0-1.5s)
    if elapsed<1.5:
        phase1=elapsed/1.5

        # Draw main circle with varying density
        circle_points=int(120+phase1*180)
        for i in range(circle_points):
            angle=i*TAU/circle_points
            x=cx+math.cos(angle)*radius
            y=cy+math.sin(angle)*radius*0.5

            # Pulsing brightness
            brightness=abs(math.sin(elapsed*4+angle*2))

            if brightness>0.7:
                c.put(x,y,'●',W)
            elif brightness>0.4:
                c.put(x,y,'○',B)
            else:
                c.put(x,y,'·',N)

            # Trailing particles expanding outward
            if phase1>0.3 and i%8==0:
                for trail in range(4):
                    trail_progress=(phase1-0.3)/0.7-trail*0.08
                    if trail_progress>0:
                        trail_radius=radius*(1+trail_progress*0.5)
                        tx=cx+math.cos(angle)*trail_radius
                        ty=cy+math.sin(angle)*trail_radius*0.5
                        if l<tx<r and top<ty<bt:
                            c.put(tx,ty,'*' if trail==0 else '+' if trail==1 else '·',
                                  W if trail==0 else B if trail==1 else N)

        # Center point
        c.put(cx,cy,'◉',R)

        # Growing label
        if phase1>0.5:
            c.center(top+2,'CIRCLE EXPANDING',W if phase1>0.8 else B)

    # Phase 2: Rotating radii explosion (1.5-2.5s)
    elif elapsed<2.5:
        phase2=(elapsed-1.5)/1.0

        # Main circle fully formed
        for i in range(180):
            angle=i*TAU/180
            x=cx+math.cos(angle)*radius
            y=cy+math.sin(angle)*radius*0.5
            brightness=(i%10==0)
            c.put(x,y,'◉' if brightness else 'o',W if brightness else B)

        # Multiple rotating radii
        num_radii=int(phase2*24)+4
        for i in range(num_radii):
            angle=i*TAU/num_radii+elapsed*1.5

            # Draw radius line with segments
            segments=int(radius)+1
            for seg in range(segments):
                r_progress=seg/segments
                rx=cx+math.cos(angle)*seg
                ry=cy+math.sin(angle)*seg*0.5

                # Gradient along radius
                if r_progress>0.8:
                    c.put(rx,ry,'═',W)
                elif r_progress>0.5:
                    c.put(rx,ry,'─',B)
                else:
                    c.put(rx,ry,'·',N)

            # Endpoint markers
            ex=cx+math.cos(angle)*radius
            ey=cy+math.sin(angle)*radius*0.5
            c.put(ex,ey,'●',Y)

        # Center
        c.put(cx,cy,'◉',R)

        # Radii count
        c.center(top+2,f'RADII: {num_radii}',W if phase2>0.7 else B)

        # Formula hint
        if phase2>0.5:
            c.center(cy-int((bt-top)*0.35),'r',Y)

    # Phase 3: Formula revelation with particle burst (2.5-3.5s)
    else:
        phase3=(elapsed-2.5)/1.0

        # Full circle
        for i in range(200):
            angle=i*TAU/200
            x=cx+math.cos(angle)*radius
            y=cy+math.sin(angle)*radius*0.5
            pulse=abs(math.sin(elapsed*3+angle*3))
            c.put(x,y,'◉' if pulse>0.7 else 'o',W if pulse>0.8 else B)

        # Selected radii
        for i in range(0,12):
            angle=i*TAU/12
            for seg in range(int(radius)):
                rx=cx+math.cos(angle)*seg
                ry=cy+math.sin(angle)*seg*0.5
                if seg%3==0:
                    c.put(rx,ry,'─',G)

        # Center
        c.put(cx,cy,'◉',R)

        # Formula builds up character by character
        formulas=[
            ('C = ?',         0.0, cy-int((bt-top)*0.2)),
            ('C = 2πr',       0.3, cy-int((bt-top)*0.2)),
            (f'C ≈ {2*3.14159*radius:.1f}', 0.6, cy),
        ]

        for formula,threshold,y_pos in formulas:
            if phase3>=threshold:
                reveal_progress=(phase3-threshold)*5
                chars_shown=min(len(formula),int(reveal_progress*len(formula)))
                shown=formula[:chars_shown]
                c.center(y_pos,shown,W if phase3>threshold+0.2 else B)

        # Arc length markers radiating out
        if phase3>0.7:
            for i in range(0,180,15):
                angle=i*TAU/180
                for pulse_dist in range(3):
                    px=cx+math.cos(angle)*(radius+5+pulse_dist*3+phase3*10)
                    py=cy+math.sin(angle)*(radius+5+pulse_dist*3+phase3*10)*0.5
                    if l<px<r and top<py<bt:
                        c.put(px,py,'*' if pulse_dist==0 else '·',
                              W if pulse_dist==0 else B if pulse_dist==1 else N)

        # Circumference label
        if phase3>0.8:
            c.center(bt-3,'CIRCUMFERENCE = 2πr',W if int(elapsed*4)%2 else B)

def lyric_sine_tangent(c,t,area,elapsed):
    """If I'm a sine wave - sine with tangent lines demonstration"""
    l,top,r,bt=area;cx,cy=(l+r)//2,(top+bt)//2
    progress=clamp(elapsed/3.0)

    # Draw sine wave
    for x in range(l+1,r):
        angle=(x-l)/(r-l)*TAU*2.5-t*0.5
        y=cy+math.sin(angle)*(bt-top)*0.25
        c.put(x,y,'~' if (x-l)%2 else '≈',B if (x-l)%3 else N)

    # Draw tangent lines at specific points
    num_tangents=int(progress*5)+1
    for i in range(min(num_tangents,5)):
        # Position along the wave
        t_point=i/4
        wave_x=l+(r-l)*t_point
        angle=(wave_x-l)/(r-l)*TAU*2.5-t*0.5
        wave_y=cy+math.sin(angle)*(bt-top)*0.25

        # Draw point
        c.put(wave_x,wave_y,'●',W if i==num_tangents-1 else Y)

        # Calculate tangent slope: derivative of sin is cos
        slope=math.cos(angle)*(bt-top)*0.25/(r-l)*TAU*2.5

        # Draw tangent line
        tangent_len=min(r-l,bt-top)*0.15
        for tx in range(-int(tangent_len),int(tangent_len)):
            tangent_x=wave_x+tx
            tangent_y=wave_y+slope*tx
            if l<tangent_x<r and top<tangent_y<bt:
                c.put(tangent_x,tangent_y,'─' if abs(slope)<0.3 else '/' if slope>0 else '\\',
                      Y if i==num_tangents-1 else G)

    # Show derivative formula
    if progress>0.3:
        c.center(top+2,'y = sin(x)',B)
    if progress>0.6:
        c.center(top+4,"y' = cos(x)",W)
    if progress>0.8:
        c.center(bt-2,'TANGENT LINES',G)

def lyric_infinity_limit(c,t,area,elapsed):
    """A luminous, data-bearing infinity ribbon is bounded by YOU."""
    l,top,r,bt=area;cx,cy=(l+r)/2,(top+bt)/2
    rail=max(9,min(16,c.w//8))
    ml=l+rail+2;mr=r-rail-2
    mw=mr-ml+1
    growth=clamp(elapsed/1.64)
    closing=clamp((t-42.346)/(43.507-42.346))
    locked=t>=43.507
    bound_l=ml+int(mw*.075*closing);bound_r=mr-int(mw*.075*closing)
    radius_x=mw*.47*(.76+.24*growth)
    radius_y=max(2,(bt-top-7)*.43)
    counter=int(8+elapsed*elapsed*39)
    c.center(top,'INFINITE LOOP / n -> INF',W)
    c.center(top+1,'[ LIMITATIONS / BOUND BY YOU ]' if locked else 'YOU.LIMIT / BOUNDARY ACQUIRED' if closing else 'GROWTH RATE: EXPONENTIAL',B)
    # Full-height registers convey growth, rather than a small isolated symbol.
    for side,x in enumerate((l,r-rail+1)):
        c.box(x,top+3,rail,bt-top-4,G)
        c.put(x+1,top+3,'N -> INF' if side==0 else 'YOU.LIMIT',B)
        for row in range(top+4,bt-2):
            n=max(0,counter+(row-top)*(1 if side==0 else -1))
            text=f'2^{n:04d}' if side==0 else f'{hash16(n*17):04X} '+('CAP' if locked else 'SET')
            c.put(x+1,row,text[:rail-2],W if (row+int(elapsed*12))%7==0 else N if side==0 else G)
    # A faint coordinate volume fills the area behind the interlaced ribbon.
    for yy in range(top+3,bt-2,3):
        for xx in range(ml,mr+1,5):c.put(xx,yy,'+',G)
    def position(a,strand=0,scale=1):
        sn=math.sin(a);cs=math.cos(a)
        denom=1+sn*sn
        x=cx+radius_x*cs/denom*scale
        y=cy+radius_y*2.8*sn*cs/denom*scale
        # Cross-section twists turn the curves into a woven character ribbon.
        x+=strand*math.cos(a*3+elapsed)*.6
        y+=strand*math.sin(a*3+elapsed)*.55
        return max(bound_l,min(bound_r,x)),y
    # Dim, offset echoes exploit CRT persistence without obscuring the main shape.
    for scale in (.80,1.10):
        for i in range(210):
            a=i*TAU/210
            x,y=position(a,0,scale)
            if top+3<y<bt-2:c.put(x,y,'.',G)
    points=[]
    for i in range(320):
        a=i*TAU/320
        z=math.sin(a+elapsed*.35)
        for strand in range(-2,3):
            x,y=position(a,strand)
            if top+3<y<bt-2:
                char='#' if abs(strand)==2 else '01'[(i+int(elapsed*18))%2]
                points.append((z,x,y,char,W if z>.65 and abs(strand)==2 else B if z>0 else N))
    for _,x,y,char,ink in sorted(points):c.put(x,y,char,ink)
    # Bright trains orbit the complete figure-eight in both directions.
    for packet in range(12):
        direction=1 if packet%2 else -1
        phase=direction*(elapsed*(1.6+growth*1.1))+packet*TAU/12
        for tail in range(7):
            x,y=position(phase-direction*tail*.025)
            if top+3<y<bt-2:c.put(x,y,'@' if tail==0 else '*' if tail<3 else '.',W if tail<2 else B if tail<4 else G)
    # Limit rails advance inward when "you can be my" begins.
    if closing>0:
        for x in (bound_l,bound_r):
            c.line(x,top+3,x,bt-3,'|' if locked else ':',W if locked else B)
            for yy in (top+3,bt-3):c.put(x-1,yy,'[+]',W)
        c.put(bound_r-2,cy,'YOU',W)
    clear(c,int(cx)-3,int(cy),7,1)
    c.put(cx-2,cy,'[ME]',W)
    c.center(bt-1,'while (me < you.limit) { grow(); }' if locked else f'n = 2^{counter:04d} / NO UPPER BOUND',B)
    c.center(bt,'LIMIT = YOU' if locked else 'DATA CIRCULATING / LOOP CONTINUES',W if locked else N)


def lyric_ac_dc(c,t,area,elapsed):
    """Split-screen AC sine wave and a DC voltage step, like a CRT scope."""
    l,top,r,bt=area;cx,cy=(l+r)//2,(top+bt)//2
    amplitude=max(2,(bt-top-4)*.29)
    left_span=max(1,cx-l-2)
    phase=elapsed*3.1
    # A quiet, delayed trace supplies the phosphor tail behind the moving AC wave.
    for trail in (1,0):
        previous=None
        for sample in range(left_span*3+1):
            xx=l+1+sample/3
            yy=cy-math.cos((xx-l-1)/left_span*TAU*2-phase+trail*.13)*amplitude
            if previous:
                px,py=previous
                c.line(px,py,xx,yy,':' if trail else '.',G if trail else N)
            previous=(xx,yy)
    # The new DC level sweeps across the old one, then holds steady.
    dc_progress=clamp((t-45.85)/1.10)
    edge=int(mix(r,cx+1,dc_progress))
    low=int(cy+amplitude);high=int(cy-amplitude)
    if edge>cx+1:c.line(cx+1,low,edge,low,':',N)
    if edge<r:
        c.line(edge,high,r,high,':',B)
        if dc_progress<1:
            c.line(edge,low,edge,high,'|',G)
            c.put(edge,high,'+',W)
    # A full-height dividing line separates the two current modes.
    c.line(cx,top,cx,bt-1,'|',B)
    c.put(cx,top,'+',W)
    c.put(cx,bt-1,'+',B)

    # The same five-row character shapes as the player's existing bitmap font.
    glyphs={'A':('01110','11011','11111','11011','11011'),
            'C':('01111','11000','11000','11000','01111'),
            'D':('11110','11011','11011','11011','11110')}
    sx=max(1,min(3,c.w//60));sy=max(1,min(3,(bt-top)//12))
    label_w=11*sx;label_h=5*sy
    label_y=cy-label_h//2
    def label(x,text,ink):
        clear(c,x-1,label_y-1,label_w+2,label_h+2)
        for index,ch in enumerate(text):
            for dy,row in enumerate(glyphs[ch]):
                for dx,pixel in enumerate(row):
                    if pixel=='1':
                        for yy in range(sy):
                            c.put(x+(index*6+dx)*sx,label_y+dy*sy+yy,'#'*sx,ink)
    # AC sits against the outer edge; DC occupies the center of the right half.
    label(l+2,'AC',W if t<46.45 else B)
    label((cx+r)//2-label_w//2,'DC',W if t>=45.85 else N)
    c.center(bt,'to AC, to DC',B)


def lyric_dizzy(c,t,area,elapsed):
    """Blind my vision - intense visual distortion with eyes everywhere"""
    l,top,r,bt=area;cx,cy=(l+r)//2,(top+bt)//2
    progress=clamp(elapsed/3.5)

    # Phase 1: Eyes opening everywhere (0-1s)
    if elapsed<1:
        phase1=elapsed/1.0
        num_eyes=int(phase1*30)+5

        for i in range(num_eyes):
            # Random but stable positions
            angle=i*TAU/30+hash16(i*13)*0.01
            radius=hash16(i*17)%(min(r-l,bt-top)//3)+10
            ex=cx+math.cos(angle)*radius
            ey=cy+math.sin(angle)*radius*0.5

            # Eye blink cycle
            blink_phase=(elapsed*3+i*0.3)%1.0
            if blink_phase<0.7:  # Open
                # Draw eye
                c.put(ex-1,ey,'(',N)
                c.put(ex,ey,'○',W if i==num_eyes-1 else B)
                c.put(ex+1,ey,')',N)
            elif blink_phase<0.85:  # Half closed
                c.put(ex-1,ey,'(',G)
                c.put(ex,ey,'-',B)
                c.put(ex+1,ey,')',G)

        c.center(top+2,'VISION',W if phase1>0.7 else B)

    # Phase 2: Spiral distortion with multiplying eyes (1-2s)
    elif elapsed<2:
        phase2=(elapsed-1)/1.0

        # Spiral vortex
        for ring in range(20):
            ring_radius=ring*4+phase2*20
            points_in_ring=max(8,int(ring*2))
            for i in range(points_in_ring):
                angle=i*TAU/points_in_ring+elapsed*2-ring*0.3
                x=cx+math.cos(angle)*ring_radius
                y=cy+math.sin(angle)*ring_radius*0.5

                if l<x<r and top<y<bt:
                    # Eyes in spiral
                    if i%3==0:
                        c.put(x,y,'◉',W if ring<5 else B if ring<12 else N)
                    else:
                        c.put(x,y,'·',N)

        # Large central eyes
        num_center_eyes=int(phase2*8)+1
        for i in range(num_center_eyes):
            eye_x=cx+int(math.sin(elapsed*4+i)*25)
            eye_y=cy+int(math.cos(elapsed*3+i*0.7)*10)

            # Animated iris following rotation
            iris_offset=int(math.sin(elapsed*5+i)*2)
            c.put(eye_x-2,eye_y,'(',B)
            c.put(eye_x-1+iris_offset,eye_y,'●',R if i%3==0 else W)
            c.put(eye_x+2,eye_y,')',B)

        c.center(cy-int((bt-top)*0.3),'DIZZY',W if int(elapsed*6)%2 else B)

    # Phase 3: Intense distortion - screen filled with eyes (2-3.5s)
    else:
        phase3=(elapsed-2)/1.5

        # Waves of distortion
        wave_intensity=phase3*8

        # Fill screen with eyes at varying depths
        for row in range(top+2, bt-2, 2):
            for col in range(l+3, r-3, 8):
                # Wave distortion
                wave_x=int(math.sin(row*0.2+elapsed*3)*wave_intensity)
                wave_y=int(math.cos(col*0.15+elapsed*2.5)*wave_intensity*0.5)

                x=col+wave_x
                y=row+wave_y

                if l+2<x<r-2 and top+1<y<bt-1:
                    # Distance from center affects eye style
                    dx,dy=x-cx,(y-cy)*2
                    dist=math.hypot(dx,dy)

                    # Pupil direction follows wave
                    pupil_dir=int(math.sin(dist*0.1+elapsed*4))

                    # Eye types based on distance
                    if dist<20:
                        # Close eyes - large and detailed
                        if hash16(row+col)%4==0:
                            c.put(x-2,y,'(',W)
                            c.put(x-1+pupil_dir,y,'●',R)
                            c.put(x+2,y,')',W)
                    elif dist<50:
                        # Medium eyes
                        if hash16(row*7+col*11)%3==0:
                            c.put(x-1,y,'(',B)
                            c.put(x+pupil_dir,y,'○',W if int(elapsed*8)%3==0 else B)
                            c.put(x+1,y,')',B)
                    else:
                        # Distant eyes - small
                        if hash16(row*13+col*17)%5==0:
                            c.put(x,y,'◉' if hash16(row+col+int(elapsed*10))%2 else '○',
                                  N if dist>80 else G)

        # Giant central eye blinking
        if phase3>0.3:
            blink=(elapsed*2)%1.0
            if blink<0.6:  # Open
                eye_size=int(8+math.sin(elapsed*5)*2)
                # Left eyelid
                for i in range(eye_size):
                    c.put(cx-eye_size+i,cy-2,'-' if i%2 else '_',W)
                # Right eyelid top
                for i in range(eye_size):
                    c.put(cx+i,cy-2,'-' if i%2 else '_',W)

                # Iris and pupil
                c.put(cx-1,cy,'(',B)
                c.put(cx,cy,'●',R if int(elapsed*4)%2 else W)
                c.put(cx+1,cy,')',B)

                # Bottom eyelid
                for i in range(eye_size):
                    c.put(cx-eye_size+i,cy+2,'_' if i%2 else '-',W)
                for i in range(eye_size):
                    c.put(cx+i,cy+2,'_' if i%2 else '-',W)
            else:  # Blinking
                for i in range(16):
                    c.put(cx-8+i,cy,'=' if i%2 else '-',B)

        # Disorienting text
        messages=['VISION','BLINDED','DIZZY','EYES','SEEING','BLIND']
        if phase3>0.5:
            for i,msg in enumerate(messages):
                msg_x=cx+int(math.sin(elapsed*3+i)*40)
                msg_y=cy+int(math.cos(elapsed*2.5+i*0.8)*15)
                if top+2<msg_y<bt-2:
                    # Distorted text
                    msg_distorted=''.join(ch if hash16(j*19+int(elapsed*10))%4>0
                                          else chr(33+hash16(j*23+i)%94)
                                          for j,ch in enumerate(msg))
                    c.center(msg_y,msg_distorted[:10],
                             W if i==int(elapsed*3)%len(messages) else B if i%2 else N)

        # Final flash effect
        if phase3>0.9 and int(elapsed*12)%3==0:
            c.center(cy,'BLIND',W)

def lyric_time_travel(c,t,area,elapsed):
    """Travel AD to BC - timeline with sweeping beam and year markers"""
    l,top,r,bt=area;cx,cy=(l+r)//2,(top+bt)//2
    progress=clamp(elapsed/3.7)

    # Timeline horizontal line
    timeline_y=cy
    for x in range(l+5, r-5):
        c.put(x, timeline_y, '─', B if x%2 else N)

    # Year markers along timeline
    # AD years on right, BC years on left
    num_markers=10
    marker_spacing=(r-l-20)//num_markers

    for i in range(num_markers):
        marker_x=l+10+i*marker_spacing

        # Tick marks
        for tick_y in range(-3, 4):
            if abs(tick_y)==3:
                c.put(marker_x, timeline_y+tick_y, '|', G if i%2 else N)
            elif abs(tick_y)==2:
                c.put(marker_x, timeline_y+tick_y, '│', G)

        # Year labels
        # Center is year 0, right is AD (positive), left is BC (negative)
        year_offset=(i-num_markers//2)*500  # 500 year intervals
        if year_offset>0:
            label=f'{abs(year_offset)}AD'
            c.center(timeline_y-5, label, Y if marker_x<r-20 else W)
            # Position near marker
            c.put(marker_x-len(label)//2, timeline_y-5, label, B)
        elif year_offset<0:
            label=f'{abs(year_offset)}BC'
            c.center(timeline_y-5, label, Y if marker_x>l+20 else W)
            c.put(marker_x-len(label)//2, timeline_y-5, label, B)
        else:
            c.put(marker_x-1, timeline_y-5, '0', W)

    # Sweeping vertical beam traveling from right (AD) to left (BC)
    beam_progress=progress
    beam_x=int(mix(r-10, l+10, beam_progress))

    # Draw the beam
    for y in range(top+2, bt-2):
        # Intensity varies along beam height
        intensity=1.0-abs(y-cy)/(bt-top)*2

        if intensity>0.7:
            c.put(beam_x, y, '│', W)
        elif intensity>0.4:
            c.put(beam_x, y, '┊', B)
        else:
            c.put(beam_x, y, ':', N)

        # Glow effect around beam
        for glow_offset in [-2,-1,1,2]:
            gx=beam_x+glow_offset
            if l<gx<r and top<y<bt:
                if abs(glow_offset)==1:
                    c.put(gx, y, '░', B if intensity>0.5 else N)
                else:
                    c.put(gx, y, '·', N)

    # Particles flying past the beam
    if progress>0.2:
        for particle_i in range(30):
            # Particle position relative to beam
            particle_phase=(elapsed*2+particle_i*0.3)%1.0

            # Horizontal position - moving left
            px=beam_x+int((particle_phase-0.5)*60)

            # Vertical position - scattered
            py=top+5+(particle_i*7)%(bt-top-10)

            if l<px<r and top<py<bt:
                if particle_phase<0.2 or particle_phase>0.8:
                    c.put(px, py, '*', W if particle_phase<0.1 else B)
                else:
                    c.put(px, py, '·', N)

    # Current year display near beam
    if progress>0.1:
        current_year=int(mix(2000, -2000, beam_progress))
        year_label=f'{abs(current_year)}{"AD" if current_year>0 else "BC" if current_year<0 else ""}'

        # Display year near beam top
        label_x=beam_x-len(year_label)//2
        if l+5<label_x<r-15:
            c.put(label_x, top+3, year_label, W if int(elapsed*4)%2 else Y)

    # Era labels
    if progress<0.3:
        c.center(top+1, 'FUTURE → PAST', B)
    elif progress<0.7:
        c.center(top+1, 'TIME TRAVEL', W if int(elapsed*3)%2 else B)
    else:
        c.center(top+1, 'ANCIENT ERA', W)

    # Speed lines indicating motion
    if progress>0.3:
        for line_i in range(15):
            line_y=top+5+line_i*((bt-top-10)//15)
            # Lines move from right to left
            line_phase=(elapsed*3+line_i*0.1)%1.0
            line_length=int(line_phase*20)+5

            for lx in range(max(l+5, beam_x+10), min(r-5, beam_x+10+line_length)):
                if hash16(line_i*17+int(lx/3))%4==0:
                    c.put(lx, line_y, '=' if line_phase>0.7 else '-',
                          B if line_phase>0.5 else N)

    # Destination marker
    if progress>0.8:
        dest_x=l+15
        c.put(dest_x, timeline_y-2, '▼', R)
        c.put(dest_x-2, timeline_y-3, 'BC', R)

        # Arrival flash
        if progress>0.95:
            flash_radius=int((progress-0.95)*60)
            for angle_i in range(12):
                angle=angle_i*TAU/12
                fx=dest_x+int(math.cos(angle)*flash_radius)
                fy=timeline_y+int(math.sin(angle)*flash_radius*0.5)
                if l<fx<r and top<fy<bt:
                    c.put(fx, fy, '*', W if flash_radius<10 else B)

def lyric_unite_deeply(c,t,area,elapsed):
    """Unite so deeply - two forms merging"""
    l,top,r,bt=area;cx,cy=(l+r)//2,(top+bt)//2
    progress=clamp(elapsed/1.8)
    # Two circles moving together
    sep=mix(40,0,progress)
    for side,label in [(-1,'ME'),(1,'YOU')]:
        center_x=cx+side*sep
        radius=15
        for i in range(60):
            angle=i*TAU/60+t*side*0.2
            x=center_x+math.cos(angle)*radius
            y=cy+math.sin(angle)*radius*0.5
            c.put(x,y,'@' if progress>0.7 and sep<5 else '*' if progress>0.4 else '.',
                  W if progress>0.8 else B if progress>0.5 else N)
        if sep>10:
            c.put(center_x,cy-2,label,B)
    if progress>0.7:
        c.center(cy,'UNIFIED',W)

def lyric_stimulation_satisfaction(c,t,area,elapsed):
    """Give sensory impulses to YOU, then fill its satisfaction meter."""
    l,top,r,bt=area;cx,cy=(l+r)//2,(top+bt)//2
    if t>=62.589:
        # Reach maximum on the sung SATISFACTION, then hold it.
        u=clamp((t-62.589)/(65.397-62.589))
        percent=int(100*u)
        full=u>=1
        c.center(max(top,cy-7),f'SATISFACTION {percent:05.1f}%',W if full else B)
        bar_x=l+3;bar_w=r-l-6;inside=bar_w-2
        for lane in range(3):
            y=cy-5+lane*2
            amount=clamp(u-(1-u)*lane*0.13)
            filled=int(inside*amount)
            c.put(bar_x,y,'['+'-'*inside+']',N)
            for col in range(filled):
                scan=(col-int(t*26)-lane*7)%max(1,inside)
                c.put(bar_x+1+col,y,'#' if lane==1 else '=',W if scan<5 or full else B)
            if filled<inside:c.put(bar_x+1+filled,y,'>',W)
        c.big(cy+1,str(percent),W if full else B)
        c.center(min(bt,cy+7),'[ MAXIMUM ]' if full else '[ FILLING SATISFACTION ]',W if full else N)
        return

    # Parallel sensory paths: the giver drives each receiver with more pulses.
    strength=clamp(elapsed/(61.958-59.223))
    accent=t>=61.958
    c.center(top,'STIMULATION / SENSORY INPUT',W if accent else B)
    left_x=l+1;right_x=r-10
    for x,label in ((left_x,'ME'),(right_x,'YOU')):
        c.box(x,cy-2,10,5,B)
        c.put(x+3,cy,label,W)
    wire_l=left_x+12;wire_r=right_x-3;span=wire_r-wire_l
    lanes=5 if bt-top>=22 else 3
    gap=max(2,min(4,(bt-top-6)//max(1,lanes-1)))
    names=['TOUCH','SOUND','LIGHT','REWARD','FEEDBACK']
    for lane in range(lanes):
        y=cy+(lane-lanes//2)*gap
        c.line(left_x+9,cy,wire_l,cy,'-',G)
        c.line(wire_l,cy,wire_l,y,'|',G)
        c.line(wire_l,y,wire_r,y,'-',N)
        c.line(wire_r,y,wire_r,cy,'|',G)
        c.line(wire_r,cy,right_x,cy,'-',G)
        c.put(wire_l+2,y-1,names[lane],N)
        for relay in (1,2):
            rx=wire_l+span*relay//3
            c.put(rx,y,'o',B)
        speed=0.65+strength*0.75
        for packet in range(3):
            phase=(elapsed*speed-lane*0.17-packet/3)%1
            head=wire_l+int(phase*span)
            for trail in range(5):
                xx=head-trail
                if xx>wire_l:c.put(xx,y,'*' if trail==0 else '=' if trail<3 else '.',W if trail==0 else B if trail<3 else G)
            if phase>0.88:
                c.put(wire_r,y,'#',W)
                c.put(right_x+1,cy+1,'ACTIVE',W)
        if accent:
            for xx in range(wire_l+1,wire_r):
                if (xx+int(t*30)+lane)%7<2:c.put(xx,y,'#',W)
    c.center(bt,f'INPUT {int(strength*100):03d}%  /  ALL CHANNELS '+('ACTIVE' if accent else 'CONNECTING'),B)

def lyric_happy_execution(c,t,area,pulse):
    """A happiness condition feeds a self-execution, with live data on both sides."""
    l,top,r,bt=area;cx,cy=(l+r)//2,(top+bt)//2
    elapsed=t-66.601
    loading=t>=68.252
    executing=t>=69.259
    rail=max(13,min(24,c.w//5))
    left=l;right=r-rail+1
    mid_l=left+rail+2;mid_r=right-3;mw=mid_r-mid_l+1
    frame=int(elapsed*(30 if executing else 18 if loading else 10))
    ops=('READ','LOAD','PUSH','COPY','SYNC','CALL','EXEC','WAIT')
    # Scroll memory upward on the left and the instruction queue downward on the right.
    for x,label,side in ((left,'MEM / YOU',0),(right,'EXEC / ME',1)):
        c.box(x,top,rail,bt-top+1,B)
        c.put(x+2,top,label[:rail-4],W)
        for row in range(top+1,bt):
            index=frame+(row-top) if side==0 else frame-(row-top)
            value=hash16(index*73+side*911)
            address=(index*16)&65535
            if side==0:
                text=f'{address:04X} {value:04X} {hash16(index*29):04X}'
            else:
                op='EXEC' if executing and index%3==0 else ops[index%len(ops)]
                text=f'{op} {address:04X} {value:04X}'
            selected=(row-top+frame)%(bt-top-1)==0
            c.put(x+1,row,('>' if selected else ' ')+text[:rail-3],W if selected else N if index%3 else G)
    def middle(y,text,style=N):
        text=text[:mw]
        c.put(mid_l+(mw-len(text))//2,y,text,style)

    middle(top,'IF (YOU.HAPPY) -> EXECUTE(ME)',W if loading else B)
    middle(top+1,'SELF.EXECUTION / '+('RUNNING' if executing else 'ARMED' if loading else 'CONDITION'),N)
    content_top=top+3;content_bt=bt-3
    center_y=(content_top+content_bt)/2
    half_h=max(2,(content_bt-content_top)*0.43)
    half_w=max(5,mw*0.40)
    beat=1+0.045*math.sin(elapsed*TAU*2)+pulse*0.04
    morph=clamp((t-68.252)/(69.259-68.252)) if loading else 0
    # A large data-filled heart. Its own cells become the execution buffer.
    for yy in range(content_top,content_bt+1):
        for xx in range(mid_l,mid_r+1):
            nx=(xx-cx)/(half_w*beat)
            ny=-(yy-center_y)/(half_h*beat)+0.20
            heart=(nx*nx+ny*ny-1)**3-nx*nx*ny**3
            seed=hash16(xx*79+yy*233)
            if heart<=0 and not executing:
                if seed/65535<morph:
                    # Removed heart cells spread out across the entire center.
                    dx=int((xx-cx)*morph*0.9)
                    dy=int((yy-center_y)*morph*0.6)
                    px=max(mid_l,min(mid_r,xx+dx));py=max(content_top,min(content_bt,yy+dy))
                    c.put(px,py,'01EX'[seed%4],G if morph>.7 else N)
                else:
                    scan=(yy-content_top-int(elapsed*9))%max(1,content_bt-content_top+1)
                    # Use the implicit equation only as a silhouette mask. Its magnitude
                    # has three interior basins, so thresholding it creates false holes.
                    texture=hash16(seed+frame//2)
                    c.put(xx,yy,'01'[texture%2] if texture%8<2 else '#',W if scan<2 else B)
            elif executing:
                # Expanding execution wave and dim opcode fragments behind the title.
                radius=abs(xx-cx)/max(1,mw/2)+abs(yy-center_y)/max(1,half_h)
                wave=((t-69.259)*3)%2
                if abs(radius-wave)<.12:c.put(xx,yy,'=',B)
                elif seed%31==0:c.put(xx,yy,'01'[seed%2],G)

    # Bright data packets flow from both edge panels into the center.
    for lane in range(3):
        yy=int(center_y)+(lane-1)*max(1,int(half_h*.7))
        path=max(2,(mw-6)//2)
        head=int(elapsed*(28 if loading else 16)+lane*7)%path
        for tail in range(4):
            step=max(0,head-tail)
            ink=W if tail==0 else B if tail<2 else G
            for xx,head_char in ((mid_l+step,'>'),(mid_r-step,'<')):
                nx=(xx-cx)/(half_w*beat)
                ny=-(yy-center_y)/(half_h*beat)+.20
                inside=(nx*nx+ny*ny-1)**3-nx*nx*ny**3<=0
                if inside and not loading:
                    # Packets brighten the solid fill instead of cutting dark dashes into it.
                    c.put(xx,yy,'#' if tail==0 else '01'[(xx+yy+frame)%2],W if tail==0 else B)
                else:
                    c.put(xx,yy,head_char if tail==0 else '-',ink)
    if executing:
        title_y=int(center_y)-2
        # Reserve a clean five-row band so the word remains legible through the wave.
        clear(c,mid_l,title_y,mw,5)
        if mw>=53:c.big(title_y,'EXECUTION',W)
        else:middle(title_y+2,'>> EXECUTION <<',W)
        middle(title_y-2,'[ YOU.HAPPY == TRUE ]',B)
        middle(title_y+6,'world.execute(me);',W)
    elif loading:
        middle(int(center_y),'[ RUN THE EXECUTION ]',W)
    else:
        middle(int(center_y),'YOU.HAPPY',W)
    middle(bt-1,'EXECUTION: '+('RUN' if executing else 'QUEUED' if loading else 'READY'),B)
    middle(bt,'ME -> YOU / '+('SELF COMMITTED' if executing else 'COMPILING...' if loading else 'MAKE YOU HAPPY'),N)


def lyric_trapped_simulation(c,t,area,pulse):
    """The execution closes a shared cage, then reveals an endless simulated space."""
    l,top,r,bt=area;cx,cy=(l+r)//2,(top+bt)//2
    age=t-70.084
    strange=clamp((t-71.764)/1.405)
    reveal=t>=73.169
    rail=max(10,min(19,c.w//6))
    ml=l+rail+1;mr=r-rail-1;mw=mr-ml+1
    inner_top=top+2;inner_bt=bt-2
    hh=max(2,(inner_bt-inner_top)/2)
    center_y=(inner_top+inner_bt)/2
    frame=int(age*(22+strange*20))
    def middle(y,text,style=N):
        text=text[:mw]
        c.put(ml+(mw-len(text))//2,y,text,style)

    # Full-height memory walls scroll in opposite directions and keep resetting.
    for x,label,direction in ((l,'HEAP / ME',1),(r-rail+1,'STACK / YOU',-1)):
        c.box(x,top,rail,bt-top+1,B)
        c.put(x+1,top,label[:rail-2],W)
        for yy in range(top+1,bt):
            step=(frame*direction+yy-top)%256
            value=hash16(step*53)
            text=(f'{step*16:04X} {value:04X}' if step%4 else ('LOOP ' if step%8 else 'EXEC ')+f'{value:04X}')
            c.put(x+1,yy,text[:rail-2],W if step%13==0 else N if step%3 else G)

    # A warped coordinate lattice covers the whole central simulation volume.
    for yy in range(inner_top,inner_bt+1):
        for xx in range(ml,mr+1):
            bend=math.sin((yy-center_y)*.32+age*3.1)*strange*6
            gx=int(xx+bend+age*5)
            gy=int(yy+math.sin((xx-cx)*.12-age*2)*strange*3)
            if gx%8==0 or gy%4==0:
                ch='+' if gx%8==0 and gy%4==0 else ':' if gx%8==0 else '.'
                c.put(xx,yy,ch,G)
            elif hash16(xx*17+yy*79+frame//3)%109==0:
                c.put(xx,yy,'01'[hash16(xx+yy)%2],N)

    # Recurring perspective frames: every apparent exit leads into another cell.
    for layer in range(8):
        phase=(layer/8+age*(.20+strange*.25))%1
        scale=.12+.88*phase**1.5
        skew=math.sin(age*2+layer*.8)*strange*mw*.10
        x0=cx-mw*.48*scale;x1=cx+mw*.48*scale
        y0=center_y-hh*.95*scale;y1=center_y+hh*.95*scale
        corners=[(x0+skew,y0),(x1,y0+strange*math.sin(age*3+layer)),
                 (x1-skew,y1),(x0,y1-strange*math.sin(age*3+layer))]
        for index in range(4):
            x,y=corners[index];xx,yy=corners[(index+1)%4]
            c.line(max(ml,min(mr,x)),y,max(ml,min(mr,xx)),yy,'=' if layer%3==0 else '-',N if layer%3==0 else G)
        if layer%2==0 and scale>.6:
            c.put(max(ml,int(x0)),int(y0),f'LOOP {layer:02d}',N)

    # The outer gate visibly contracts around both entities on "we are trapped".
    close=clamp(age/.85)
    box_w=max(20,int(mw*(.98-.22*close)))
    box_h=max(7,int((inner_bt-inner_top+1)*(.98-.16*close)))
    bx=cx-box_w//2;by=int(center_y)-box_h//2
    if not reveal:
        c.box(bx,by,box_w,box_h,B)
        # Sliding bars lock from both sides; their gaps then oscillate unnaturally.
        for index in range(1,7):
            xx=bx+index*(box_w-1)//7
            jitter=int(math.sin(age*5+index)*strange*2)
            extent=int((box_h-2)*close)
            for row in range(extent):
                yy=by+1+row if index%2 else by+box_h-2-row
                c.put(xx+jitter,yy,'|',N if index%2 else B)
        middle(by,'[ CONTAINMENT '+('LOCKED' if close>=1 else 'CLOSING')+' ]',W)
        node_y=int(center_y)
        for x,name in ((cx-max(6,box_w//4),'ME'),(cx+max(6,box_w//4),'YOU')):
            clear(c,x-4,node_y-1,9,3)
            c.box(x-4,node_y-1,9,3,W)
            c.put(x-len(name)//2,node_y,name,W)
        c.line(cx-box_w//4+5,node_y,cx+box_w//4-5,node_y,'=',B)
        if t>=71.764:middle(by+box_h-1,'STRANGE / '+f'RECURSION {int(age*13):03d}',W)
    else:
        title_y=int(center_y)-2
        clear(c,ml,title_y,mw,5)
        if mw>=59:c.big(title_y,'SIMULATION',W)
        else:middle(title_y+2,'>> SIMULATION <<',W)
        middle(title_y-2,'[ NO EXIT / SAME WORLD ]',B)
        middle(title_y+6,'[ ME ] <== LOOP ==> [ YOU ]',W)

    middle(top,'EXECUTION -> SIMULATION',B)
    middle(top+1,'world.simulate(me, you);',N)
    middle(bt-1,'EXIT: DENIED / RESTART: '+f'{int(age*17):04d}',B)
    middle(bt,'TRAPPED TOGETHER / LOOP FOREVER',W if reveal else N)


def lyric_heart(c,t,area,elapsed,pulse):
    """Heart model - pulsing 3D heart"""
    l,top,r,bt=area;cx,cy=(l+r)//2,(top+bt)//2
    # Heart shape equation
    scale=0.5+pulse*0.15+elapsed*0.03
    for angle_i in range(60):
        for rad_i in range(15):
            angle=angle_i*TAU/60
            rad=rad_i/15
            # Heart equation
            x=16*math.sin(angle)**3
            y=-(13*math.cos(angle)-5*math.cos(2*angle)-2*math.cos(3*angle)-math.cos(4*angle))
            x,y=x*scale*rad/17,y*scale*rad/17
            px,py=cx+x*4,cy+y*2
            if l<px<r and top<py<bt:
                brightness=rad*(1+pulse*0.3)
                c.put(px,py,'#' if brightness>0.8 else '*' if brightness>0.5 else '.',
                      W if brightness>0.9 else B if brightness>0.6 else N)
    if elapsed>1:
        c.center(cy,'♥',R)



# Original organic choreography restored from the first delivered version.
def legacy_panel(c,x,y,w,h,label):
    clear(c,x,y,w,h);c.box(x,y,w,h,D)
    c.put(x+2,y,' '+label[:max(0,w-6)]+' ',N)

def legacy_workspace(c,t,top,bt,label,status='ACTIVE'):
    c.put(2,top,label,W)
    c.put(max(3,c.w-len(status)-3),top,status,B)
    c.put(2,top+1,'-'*(c.w-4),G)
    side=min(25,max(17,c.w//6)) if c.w>=100 else 0
    if side:
        lx=2;rx=c.w-side-2;ph=bt-top-2
        legacy_panel(c,lx,top+2,side,ph,'REGISTER')
        legacy_panel(c,rx,top+2,side,ph,'PROCESS')
        k=int(t*7)
        left=['PID 0001 : ME','UID 0002 : YOU',f'PC  {hash16(k):04X}',f'SP  {hash16(k+3):04X}']
        right=['STATE '+status[:7],f'TICK {int(t*120):06d}',f'CALL {hash16(k+7):04X}','FLAGS Z C O S']
        height=ph-2
        for i in range(height):
            yy=top+3+i
            if i<len(left):a=left[i];b=right[i]
            elif i==5:a='HEAP ALLOCATION';b='STACK TRACE'
            else:
                j=k+i
                a=f'{(i*16):04X} {hash16(j):04X} {hash16(j+19):04X}'
                ops=['LOAD','PUSH','CALL','WAIT','COPY','SYNC','RET ','JMP ']
                b=f'{ops[j%8]} @{hash16(j*3):04X}'
            c.put(lx+2,yy,a[:side-4],N if i<4 else G)
            c.put(rx+2,yy,b[:side-4],N if i<4 else G)
        sweep=int(t*8)%max(1,height)
        c.put(lx+1,top+3+sweep,'>',B)
        c.put(rx+side-2,top+3+(height-1-sweep),'<',B)
    return (side+4 if side else 4,top+3,c.w-side-5 if side else c.w-5,bt-1)

def legacy_mesh(c,t,area,form='torus',pulse=0):
    """Depth-tested parametric point surfaces, lit in character luminance."""
    zbuf={}
    for u in range(78):
        a=u*TAU/78
        for v in range(26):
            b=v*TAU/26
            if form=='torus':x=(.76+.29*math.cos(b))*math.cos(a);y=(.76+.29*math.cos(b))*math.sin(a);z=.29*math.sin(b)
            elif form=='sphere':x=math.sin(b)*math.cos(a);y=math.cos(b);z=math.sin(b)*math.sin(a)
            elif form=='heart':
                radius=.5+.5*math.cos(b)
                x=(16*math.sin(a)**3/17)*radius
                y=-(13*math.cos(a)-5*math.cos(2*a)-2*math.cos(3*a)-math.cos(4*a))/17*radius
                z=.38*math.sin(b)*math.sin(a)
                x*=1+pulse*.12;y*=1+pulse*.12
            elif form=='eggplant':
                x=math.sin(b)*math.cos(a)*(.43+.16*math.cos(b));y=math.cos(b)*1.2;z=math.sin(b)*math.sin(a)*.6
            elif form=='tomato':x=math.sin(b)*math.cos(a);y=math.cos(b)*.68;z=math.sin(b)*math.sin(a)
            else:
                x=(.68+.25*math.cos(3*a+b))*math.cos(2*a);y=(.68+.25*math.cos(3*a+b))*math.sin(2*a);z=.5*math.sin(3*a+b)
            xx,yy,zz=point(x,y,z,area,t if form!='heart' else math.sin(t*.45)*1.2)
            p=(round(xx),round(yy))
            if p not in zbuf or zz<zbuf[p][0]:zbuf[p]=(zz,a,b)
    ramp='.,:;=+*#@'
    l,y,r,bt=area
    for (x,yy),(z,a,b) in zbuf.items():
        if not(l<=x<=r and y<=yy<=bt):continue
        light=clamp(.45-z*.30+math.sin(a*2+b+t*.3)*.13)
        c.put(x,yy,ramp[int(light*(len(ramp)-1))],B if light>.77 else N if light>.40 else G)

def legacy_ring(c,t,area,turns=3):
    l,y,r,b=area;cx=(l+r)/2;cy=(y+b)/2
    for k in range(turns):
        rr=.32+k*.058
        for i in range(140):
            a=i*TAU/140
            if (i+k*9)%23<5:continue
            x=cx+math.cos(a)*(r-l)*rr;yy=cy+math.sin(a)*(b-y)*rr
            c.put(x,yy,'.' if k%2 else ':',G if k!=1 else D)
        a=t*(.6+k*.1)+k*2
        for j in range(14):
            aa=a-j*.018
            c.put(cx+math.cos(aa)*(r-l)*rr,cy+math.sin(aa)*(b-y)*rr,'+' if j==0 else '.',W if j==0 else G)

def legacy_organic(c,t,top,bt,pulse):
    i=0 if t<77.576 else 1 if t<81.351 else 2 if t<85.078 else 3
    subject=['EGGPLANT','TOMATO','TABBY CAT','GOD'][i]
    resource=['NUTRIENTS','ANTIOXIDANTS','ENJOYMENT','EXISTENCE'][i]
    area=legacy_workspace(c,t,top,bt,'TYPE CAST / '+subject,'EXPORT')
    l,y,r,b=area;cx=(l+r)/2;cy=(y+b)/2
    if i in (0,1):legacy_mesh(c,t,(l,y,cx+6,b),'eggplant' if i==0 else 'tomato')
    elif i==2:
        vs=[(-.9,-.8,0),(-.75,.4,0),(0,.75,0),(.75,.4,0),(.9,-.8,0),(.4,-.4,0),(-.4,-.4,0),(-.28,0,-.1),(.28,0,-.1),(0,.25,-.2)]
        es=[(0,1),(1,2),(2,3),(3,4),(4,5),(5,6),(6,0),(7,9),(8,9),(5,8),(6,7)]
        projected(c,vs,es,(l,y,cx+8,b),math.sin(t)*.5)
        for s in (-1,1):
            for j in range(3):c.line(l+(cx-l)/2,cy+1,l+(cx-l)/2+s*11,cy+j-1,'.',N)
    else:legacy_mesh(c,t,(l,y,cx+8,b),'sphere');legacy_ring(c,t,(l,y,cx+8,b),4)
    target=round(mix(cx,r,.67))
    c.box(target-5,int(cy-2),11,5,N);c.put(target-3,cy,'YOU_02',W)
    for k in range(5):
        yy=cy-2+k
        c.line(cx-1,yy,target-6,yy,'.',G)
        xx=mix(cx,target-6,((t*.8+k*.2)%1))
        c.put(xx,yy,'>>',B if k==2 else D)
    c.center(y,f'convert(self, {resource.lower()});',W)
    c.center(b,f'TX {int((t%3)/3*65535):04X}  |  {resource} -> YOU  |  ACK',N)

def legacy_phosphor(c,t,top,bt):
    """Luminance scan and short signal tears, confined above the captions."""
    row=top+int(t*9)%max(1,bt-top+1)
    for x in range(2,c.w-2):
        ch,s=c.cells[row][x]
        if ch not in ('',' ') and s in (D,N,G):c.cells[row][x]=(ch,N if s==G else B)
    if 125.708<t<177.246 and int(t*13)%17 in (0,1):
        yy=top+hash16(int(t*13))%max(1,bt-top)
        shift=2 if int(t*13)%2 else -3
        source=c.cells[yy][2:-2]
        source=source[-shift:]+source[:-shift]
        c.cells[yy][2:-2]=source

def lyric_eggplant_tomato(c,t,area,item):
    """Eggplant/tomato - simple organic shape"""
    l,top,r,bt=area;cx,cy=(l+r)//2,(top+bt)//2
    # Simple blob
    for y in range(top,bt):
        for x in range(l,r):
            dx,dy=(x-cx)/4,(y-cy)/2
            dist=math.hypot(dx,dy)
            if item=='eggplant':
                # Elongated
                if dist<6 and abs(dy)<8:
                    c.put(x,y,'█' if dist<4 else '▓',B if dy<0 else N)
            else:
                # Round
                if dist<5:
                    c.put(x,y,'●' if dist<3 else 'o',R if dist<3 else N)
    c.center(cy+int((bt-top)*0.3),item.upper(),B)

def lyric_cat(c,t,area,elapsed):
    """Tabby cat - ASCII cat"""
    l,top,r,bt=area;cx,cy=(l+r)//2,(top+bt)//2
    cat=[
        "  /\\_/\\  ",
        " ( o.o ) ",
        "  > ^ <  ",
        " /|   |\\ "
    ]
    for i,line in enumerate(cat):
        c.center(cy-2+i,line,B if i<3 else N)
    # Purr waves
    if elapsed>0.5:
        for i in range(5):
            phase=(elapsed*2+i*0.2)%1
            x=cx+int(phase*20)-10
            c.put(x,cy+3,'~' if phase<0.8 else '',G)
    c.center(cy+5,'*purr*',G)

def lyric_god_existence(c,t,area,elapsed):
    """God/existence - radiant aura"""
    l,top,r,bt=area;cx,cy=(l+r)//2,(top+bt)//2
    # Radiating light
    for ring in range(8):
        radius=5+ring*4+math.sin(t*2+ring)*2
        density=60-ring*5
        for i in range(density):
            angle=i*TAU/density+t*0.1*(-1)**ring
            x=cx+math.cos(angle)*radius
            y=cy+math.sin(angle)*radius*0.5
            brightness=1-ring/8
            c.put(x,y,'*' if brightness>0.7 else '+' if brightness>0.4 else '.',
                  W if brightness>0.8 else B if brightness>0.5 else N)
    c.center(cy,'GOD',W)
    c.center(cy+2,'YOU',B)

def identity_bitmap(c,x,y,text,sx,sy,ink,fill=1,seed=0):
    glyphs={'F':('11111','11000','11110','11000','11000'),
            'M':('10001','11011','10101','10001','10001'),
            'A':('01110','11011','11111','11011','11011'),
            'P':('11110','11011','11110','11000','11000')}
    for index,ch in enumerate(text):
        for dy,row in enumerate(glyphs[ch]):
            for dx,pixel in enumerate(row):
                if pixel=='1':
                    for py in range(sy):
                        for px in range(sx):
                            xx=x+(index*6+dx)*sx+px;yy=y+dy*sy+py
                            on=hash16((index*31+dx)*73+dy*137+px*19+py+seed)/65535<=fill
                            c.put(xx,yy,'#' if on else '.',ink if on else G)


def lyric_identity_rewrite(c,t,area):
    """Rewrite a gender field by disassembling and transmitting its character cells."""
    l,top,r,bt=area;cx,cy=(l+r)//2,(top+bt)//2
    age=t-88.587
    u=clamp((t-90.197)/1.25)
    sx=max(2,min(6,(r-l)//22));sy=max(1,min(5,(bt-top-8)//5))
    glyph_w=5*sx;glyph_h=5*sy
    left_c=(l+cx)//2;right_c=(cx+r)//2;y=cy-glyph_h//2
    c.center(top,'SELF.GENDER / PARAMETER REWRITE',W)
    c.center(top+1,'F -> M / TRANSMIT IDENTITY',B)
    c.box(l,top+3,cx-l-1,bt-top-5,G)
    c.box(cx+2,top+3,r-cx-1,bt-top-5,G)
    # Scrolling bytes fill both panes, behind the large letter masks.
    for row in range(top+4,bt-2,2):
        tick=int(age*18)+row
        c.put(l+2,row,f'{hash16(tick):04X}',G)
        c.put(r-5,row,f'{hash16(tick+79):04X}',G)
    for i in range(6):
        yy=top+4+i*max(1,(bt-top-8)//5)
        c.line(l+7,yy,r-7,yy,'.',G)
        progress=(age*.9+i*.17)%1
        x=mix(left_c,right_c,progress)
        c.put(x,yy,'>>',W if u else B)
    clear(c,left_c-glyph_w//2-1,y-1,glyph_w+2,glyph_h+2)
    clear(c,right_c-glyph_w//2-1,y-1,glyph_w+2,glyph_h+2)
    identity_bitmap(c,left_c-glyph_w//2,y,'F',sx,sy,W,1-u)
    identity_bitmap(c,right_c-glyph_w//2,y,'M',sx,sy,W,u)
    # Released source cells travel in arcs and settle into the new character.
    if 0<u<1:
        for i in range(44):
            p=clamp(u*1.6-(i%11)/18)
            x=mix(left_c,right_c,p)
            yoff=(hash16(i*31)%max(1,glyph_h))-glyph_h/2
            yy=cy+yoff+math.sin(p*math.pi)*(1 if i%2 else -1)*3
            c.put(x,yy,'01#'[i%3],W if i%4==0 else B)
    c.put(left_c-4,bt-3,'SOURCE F',N if u<1 else G)
    c.put(right_c-4,bt-3,'TARGET M',W if u>=1 else N)
    c.center(bt-1,f'WRITE {int(u*100):03d}% / '+('COMMITTED' if u>=1 else 'COMPILING' if not u else 'REASSEMBLING'),B)
    c.center(bt,"self.gender = 'M';" if u>=1 else "self.gender: F -> M",W)


def lyric_daynight_clock(c,t,area):
    """An oversized clock races through daylight and flips its AM/PM display."""
    l,top,r,bt=area;cx,cy=(l+r)//2,(top+bt)//2
    age=t-92.015
    flip_at=94.55
    is_pm=t>=flip_at
    virtual=6+6*clamp((t-92.015)/(flip_at-92.015)) if not is_pm else 12+6*clamp((t-flip_at)/(95.465-flip_at))
    clock_x=(l+cx)//2;display_x=(cx+r)//2
    rx=max(6,(cx-l)*.43);ry=max(3,(bt-top-6)*.43)
    c.center(top,'CLOCK.CYCLE / AM -> PM',W)
    c.center(top+1,'DAYLIGHT -> NIGHT / TIME ACCELERATING',B)
    # Clock face fills the left half instead of occupying a small central patch.
    for i in range(180):
        a=i*TAU/180
        c.put(clock_x+math.sin(a)*rx,cy-math.cos(a)*ry,'.',N)
    for hour in range(12):
        a=hour*TAU/12
        c.line(clock_x+math.sin(a)*rx*.9,cy-math.cos(a)*ry*.9,
               clock_x+math.sin(a)*rx,cy-math.cos(a)*ry,'#',B)
        c.put(clock_x+math.sin(a)*rx*.77-1,cy-math.cos(a)*ry*.77,str(hour or 12),N)
    hour_angle=virtual/12*TAU;minute_angle=(virtual%1)*TAU
    for trail in range(4,0,-1):
        a=minute_angle-trail*.13
        c.line(clock_x,cy,clock_x+math.sin(a)*rx*.8,cy-math.cos(a)*ry*.8,'.',G)
    c.line(clock_x,cy,clock_x+math.sin(hour_angle)*rx*.52,cy-math.cos(hour_angle)*ry*.52,'#',B)
    c.line(clock_x,cy,clock_x+math.sin(minute_angle)*rx*.83,cy-math.cos(minute_angle)*ry*.83,'*',W)
    c.put(clock_x,cy,'@',W)
    c.line(cx,top+3,cx,bt-3,'|',G)
    # Day/night symbol and huge AM/PM bitmap occupy the entire right pane.
    radius=max(3,min((r-cx)*.22,(bt-top)*.34))
    for i in range(120):
        a=i*TAU/120
        x=display_x+math.cos(a)*radius*1.6;y=cy+math.sin(a)*radius
        if not is_pm or math.cos(a)<.45:c.put(x,y,':',G if is_pm else N)
    if not is_pm:
        for ray in range(16):
            a=ray*TAU/16+age*.25
            c.line(display_x+math.cos(a)*radius*1.8,cy+math.sin(a)*radius*1.1,
                   display_x+math.cos(a)*radius*2.1,cy+math.sin(a)*radius*1.3,'.',G)
    else:
        for star in range(22):
            x=cx+2+hash16(star*31)%max(1,r-cx-4)
            y=top+3+hash16(star*79)%max(1,bt-top-6)
            c.put(x,y,'+' if (int(age*5)+star)%5==0 else '.',G)
    sx=max(1,min(4,(r-cx-6)//11));sy=max(1,min(4,(bt-top-8)//5))
    glyph_w=11*sx;glyph_h=5*sy;y0=cy-glyph_h//2
    clear(c,display_x-glyph_w//2-1,y0-1,glyph_w+2,glyph_h+2)
    identity_bitmap(c,display_x-glyph_w//2,y0,'PM' if is_pm else 'AM',sx,sy,W)
    # A narrow scan sweeps down the display on the flip.
    if 0<=t-flip_at<.22:
        yy=y0+int((t-flip_at)/.22*glyph_h)
        c.put(display_x-glyph_w//2,yy,'='*glyph_w,W)
    hour=int(virtual)%24;minute=int((virtual%1)*60)
    c.put(display_x-2,min(bt-3,y0+glyph_h+1),f'{hour:02d}:{minute:02d}',W)
    c.center(bt-1,'[ PM / NIGHT CYCLE ]' if is_pm else '[ AM / DAY CYCLE ]',B)
    c.center(bt,'do_whatever();  // AM -> PM',N)


def lyric_gender_role_switch(c,t,area,elapsed,from_label,to_label):
    """Gender/role switching - full screen symbolic transformation"""
    l,top,r,bt=area;cx,cy=(l+r)//2,(top+bt)//2
    progress=clamp(elapsed/2.5)

    # ===== F→M: Gender symbols transformation =====
    if from_label=='F' and to_label=='M':
        # Full screen: ♀ symbols morphing to ♂
        for i in range(150):
            angle=i*2.4+t*0.5
            radius_base=math.sqrt(i)*4
            radius=radius_base+math.sin(t*2+i*0.1)*3
            x=cx+math.cos(angle)*radius
            y=cy+math.sin(angle)*radius*0.5

            # Morph symbol based on progress
            if progress<0.3:
                symbol='♀'
                style=W if i%5==0 else B if i%3==0 else N
            elif progress<0.7:
                # Transition phase - mix of both
                symbol='♀' if (i+int(t*10))%2==0 else '♂'
                style=R if (i+int(t*20))%3==0 else W if i%4==0 else B
            else:
                symbol='♂'
                style=W if i%5==0 else B if i%3==0 else N
            c.put(x,y,symbol,style)

        # Central explosion during transition
        if 0.3<progress<0.7:
            burst_progress=(progress-0.3)/0.4
            for burst_i in range(60):
                burst_angle=burst_i*TAU/60+t*3
                burst_r=burst_progress*50
                bx=cx+math.cos(burst_angle)*burst_r
                by=cy+math.sin(burst_angle)*burst_r*0.5
                c.put(bx,by,'⚥' if burst_i%3==0 else '*',W)

        # Large center symbol
        scale=int(8+int(math.sin(t*2)*2))
        center_symbol='♀' if progress<0.5 else '♂'
        for dy in range(-scale,scale+1):
            for dx in range(-scale*2,scale*2+1):
                dist=math.hypot(dx/2,dy)
                if dist<scale:
                    c.put(cx+dx,cy+dy,center_symbol,
                          W if dist<scale*0.4 else B if dist<scale*0.7 else N)

    # ===== AM→PM: Clock progression =====
    elif from_label=='AM' and to_label=='PM':
        # Clock face with hands sweeping
        radius_clock=int(min(r-l,bt-top)*0.35)

        # Clock circle
        for i in range(120):
            angle=i*TAU/120
            x=cx+math.cos(angle)*radius_clock
            y=cy+math.sin(angle)*radius_clock*0.5
            c.put(x,y,'○' if i%10==0 else '·',B)

        # Hour markers (12, 3, 6, 9)
        for hour in [0,3,6,9]:
            angle=hour*TAU/12-TAU/4  # -90deg offset
            x=cx+math.cos(angle)*radius_clock*0.85
            y=cy+math.sin(angle)*radius_clock*0.85*0.5
            c.put(x,y,f'{hour if hour!=0 else 12}',W)

        # Clock hands rotating from AM (6:00) to PM (18:00)
        start_hour=6
        end_hour=18
        current_hour=mix(start_hour,end_hour,progress)

        # Hour hand
        hour_angle=current_hour*TAU/12-TAU/4
        hour_length=int(radius_clock*0.5)
        for step in range(hour_length):
            x=cx+math.cos(hour_angle)*step
            y=cy+math.sin(hour_angle)*step*0.5
            c.put(x,y,'═',W if step>hour_length*0.7 else B)

        # Minute hand (spinning fast)
        minute_angle=(t*6)%TAU-TAU/4
        minute_length=int(radius_clock*0.7)
        for step in range(minute_length):
            x=cx+math.cos(minute_angle)*step
            y=cy+math.sin(minute_angle)*step*0.5
            c.put(x,y,'─',B if step>minute_length*0.8 else N)

        # Time digits cascading
        for digit_y in range(int((bt-top)*0.6)):
            phase=(progress*3+digit_y*0.05)%1
            if phase<0.8:
                digit_x=int(cx+math.sin(phase*TAU)*30)
                hour_shown=int(mix(6,18,phase))%24
                c.put(digit_x,top+digit_y,f'{hour_shown:02d}',
                      W if phase>0.6 else B if phase>0.3 else G)

        # Central display
        display_hour=int(current_hour)%24
        c.center(cy+int((bt-top)*0.25),f'{display_hour:02d}:00',W)
        c.center(cy+int((bt-top)*0.32),'AM' if current_hour<12 else 'PM',R if current_hour>=12 else B)

    # ===== S→M: Dominance to submission (chains/waves) =====
    else:  # S to M
        # Visual: Sharp edges (S) flowing into smooth curves (M)

        # Background: Transitioning pattern
        if progress<0.5:
            # S phase: Sharp angles, rigid structure
            for row in range(top,bt+1,3):
                for x in range(l,r,8):
                    offset=int((t*10+row)%8)
                    pattern='╱╲' if row%6<3 else '╲╱'
                    c.put(x+offset,row,pattern[0],N)
                    c.put(x+offset+1,row,pattern[1],N)
        else:
            # M phase: Smooth waves, flowing
            for wave_y in range(12):
                y=top+int(wave_y*(bt-top)/11)
                for x in range(l,r):
                    wave=(x-l)/(r-l)*TAU*3-t*2
                    amplitude=(bt-top)*0.1*(progress-0.5)*2
                    offset=int(math.sin(wave)*amplitude)
                    c.put(x,y+offset,'~' if wave_y%2==0 else '≈',B if wave_y%3==0 else N)

        # Center transformation
        if progress<0.4:
            # S: Angular crown/spikes
            spike_count=8
            for i in range(spike_count):
                angle=i*TAU/spike_count+t*0.5
                base_r=15
                for r_step in range(20):
                    spike_r=base_r+r_step*1.5
                    spike_x=cx+math.cos(angle)*spike_r
                    spike_y=cy+math.sin(angle)*spike_r*0.5
                    if abs(angle%(TAU/spike_count))<0.2:  # Make spikes
                        c.put(spike_x,spike_y,'▲' if r_step%2==0 else '△',
                              W if r_step>15 else B if r_step>10 else N)
        elif progress<0.6:
            # Transition: Explosion
            trans=(progress-0.4)/0.2
            for i in range(80):
                angle=i*TAU/80
                radius=trans*60
                x=cx+math.cos(angle)*radius+math.sin(t*4+i)*5*(1-trans)
                y=cy+math.sin(angle)*radius*0.5+math.cos(t*4+i)*3*(1-trans)
                c.put(x,y,'*' if i%3==0 else '·',W if trans<0.5 else B)
        else:
            # M: Soft concentric circles
            circles=(progress-0.6)/0.4
            for ring in range(8):
                ring_r=8+ring*4
                density=int(ring_r*6)
                for i in range(density):
                    angle=i*TAU/density+t*0.3*(-1)**ring
                    x=cx+math.cos(angle)*ring_r
                    y=cy+math.sin(angle)*ring_r*0.5
                    c.put(x,y,'○' if ring%2==0 else '◯',
                          W if ring<3 else B if ring<5 else N)

        # Large central letter
        size=int(10+math.sin(t*1.5)*1.5)
        if not isinstance(size, int):
            size=int(size)
        center_char='S' if progress<0.5 else 'M'
        for dy in range(-size,size+1):
            for dx in range(-size*2,size*2+1):
                dist=math.hypot(dx/2,dy)
                if size*0.3<dist<size*0.8:
                    c.put(cx+dx,cy+dy,center_char,
                          W if dist>size*0.6 else B)

    # Common elements: Status and decorations
    c.center(top,f'{from_label} → {to_label}',W if progress>0.8 else B)
    c.center(bt,f'TRANSFORMATION: {int(progress*100)}%',N)

def ecg_sample(phase):
    """Stylized P-QRS-T trace, positive values point up on the monitor."""
    points=((0,0),(.08,0),(.12,.15),(.17,0),(.28,0),(.31,-.18),
            (.35,1.0),(.39,-.32),(.43,0),(.52,0),(.60,.25),(.70,0),(1,0))
    phase%=1
    for i in range(1,len(points)):
        x1,y1=points[i];x0,y0=points[i-1]
        if phase<=x1:return mix(y0,y1,(phase-x0)/(x1-x0))
    return 0


def lyric_vibration_sync(c,t,area,elapsed):
    """Swept CRT cardiograph: feel YOU, then bring ME into the same rhythm."""
    l,top,r,bt=area
    compact=bt-top<19
    sync=clamp((t-107.22)/(110.221-107.22))
    complete=t>=110.221
    phase_lag=.28*(1-sync)
    bpm=72
    c.put(l,top,'ECG / DUAL CHANNEL',B)
    c.put(r-10,top,f'{bpm:03d} BPM',W)
    if not compact:
        title='COMPLETION / RHYTHM LOCKED' if complete else 'PHASE SYNCHRONIZING' if t>=107.22 else 'VIBRATIONS DETECTED' if t>=106.293 else 'ACQUIRING YOUR HEARTBEAT'
        c.center(top+1,title,W if complete else N)
    plot_top=top+(2 if compact else 4)
    plot_bt=bt-(1 if compact else 3)
    split=(plot_top+plot_bt)//2
    x0=l+1;x1=r-1;span=x1-x0+1
    # Three beats fit the screen. The head traverses it every 2.5 seconds.
    speed=span/2.5
    sweep=elapsed*speed+span*.30
    head=x0+int(sweep)%span
    gap=max(2,int(span*.025))
    for yy in range(plot_top,plot_bt+1):
        for xx in range(x0,x1+1):
            if (xx-x0)%10==0 and (yy-plot_top)%3==0:
                c.put(xx,yy,'+',G)
            elif (yy-plot_top)%3==0 and (xx-x0)%2==0:
                c.put(xx,yy,'.',G)
    for yy in range(plot_top,plot_bt+1):c.put(head,yy,':',G)
    for lane,(start,end,name,lag) in enumerate(((plot_top,split,'YOU',0),(split+1,plot_bt,'ME',phase_lag))):
        height=end-start+1
        baseline=start+int((height-1)*.68)
        amplitude=max(1,(height-2)*.58)
        c.put(x0,start,name,W if lane==0 or complete else N)
        previous=None
        # Sub-cell sampling connects the steep QRS spike instead of leaving isolated dots.
        for sample in range(span*4):
            xx=x0+sample/4
            age=(head-xx)%span
            if age>span-gap:
                previous=None
                continue
            signal_time=elapsed-age/speed
            phase=signal_time*bpm/60-lag
            yy=baseline-ecg_sample(phase)*amplitude
            yy=max(start,min(end,yy))
            ink=W if age<span*.10 else B if age<span*.50 else N
            if lane==1 and not complete:ink=B if age<span*.15 else N
            if previous is not None:
                px,py=previous
                # Crossing the sweep reset starts a new path; it must not create a false spike.
                if abs(age-previous_age)<2:
                    dy=yy-py
                    char='|' if abs(dy)>.65 else '/' if dy<-.13 else '\\' if dy>.13 else '-'
                    c.line(px,py,xx,yy,char,ink)
            previous=(xx,yy);previous_age=age
        tip=baseline-ecg_sample(elapsed*bpm/60-lag)*amplitude
        tip=max(start,min(end,tip))
        # Bright writing point with a short phosphor afterglow, independent of terminal theme.
        c.put(head-1,tip,'=',B)
        c.put(head,tip,'@',W)
        if not compact:
            c.put(x1-7,start,'IN SYNC' if complete else 'SENSED' if lane==0 else 'SEEKING',B if complete else N)
    indicator='*' if ecg_sample(elapsed*bpm/60)>.65 else '.'
    if not compact:
        c.put(l,bt-1,f'BEAT [{indicator}]  /  YOU -> ME',B)
        status=f'SYNC {int(sync*100):03d}%  DELAY {int(phase_lag*1000/(bpm/60)):03d}ms'
        c.put(r-len(status)+1,bt-1,status,W if complete else B)
    c.center(bt,'[ COMPLETION / HEARTBEATS SYNCHRONIZED ]' if complete else '[ FEEL YOUR VIBRATIONS ]' if t<107.22 else '[ MATCHING YOUR RHYTHM ]',W if complete else N)


def lyric_isolation_disconnect(c,t,area,elapsed):
    """Six departures follow the repeated lyric instead of breaking at once."""
    l,top,r,bt=area;cx,cy=(l+r)/2,(top+bt)/2
    rx=(r-l)*.39;ry=max(3,(bt-top-6)*.39)
    breaks=(.70,1.32,2.20,3.28,4.02,4.88)
    gone=sum(elapsed>=cut for cut in breaks)
    c.center(top,f'CONNECTION LOSS / {gone:02d} OF 06',R if gone>3 else B)
    # Radar arcs and data streams remain active through the whole isolation phrase.
    for ring in range(3):
        sweep=(elapsed*.34+ring/3)%1
        for sample in range(96):
            a=sample*TAU/96
            if sample%7<4:
                c.put(cx+math.cos(a)*rx*sweep,cy+math.sin(a)*ry*sweep,'.',G)
    for side in (0,1):
        x=l if side==0 else r-9
        for row in range(top+2,bt-1,2):
            tick=int(elapsed*13)+row*(1 if side else -1)
            c.put(x,row,f'{hash16(tick*31):04X} '+('LOST' if hash16(tick)%6<gone else 'PING'),G if side else N)
    for i,cut in enumerate(breaks):
        a=(i+.5)*TAU/6
        nx=cx+math.cos(a)*rx;ny=cy+math.sin(a)*ry
        age=elapsed-cut
        # A shared outer network also unravels as each radial connection fails.
        next_a=(i+1.5)*TAU/6
        if age<.4:
            c.line(nx,ny,cx+math.cos(next_a)*rx,cy+math.sin(next_a)*ry,':',G)
        steps=max(12,int(rx))
        rupture=clamp(age/1.1)
        for j in range(steps):
            u=j/max(1,steps-1)
            if age>=0 and abs(u-.55)<rupture*.6:continue
            jitter=math.sin(j*2+elapsed*35)*(.55 if -.35<age<.5 else .08)
            xx=mix(cx,nx,u);yy=mix(cy,ny,u)+jitter
            c.put(xx,yy,'=' if -.35<age<.2 else '.',W if -.2<age<.2 else N if age<0 else G)
        if age<0:
            for packet in range(3):
                u=(elapsed*.65+packet/3+i*.1)%1
                c.put(mix(nx,cx,u),mix(ny,cy,u),'*',W)
            c.box(int(nx)-4,int(ny)-1,9,3,B)
            c.put(nx-3,ny,f'YOU_{i+1}',W)
        else:
            # Recoil, sparks and a fading shock ring keep every break visible.
            drift=min(1,age/2)
            ox=nx+math.cos(a)*drift*4;oy=ny+math.sin(a)*drift*2
            c.put(ox-3,oy,'[LOST]',R if age<.8 else G)
            if age<2.3:
                for particle in range(22):
                    angle=hash16(i*97+particle*19)/65535*TAU
                    velocity=2+hash16(particle*17+i)%8
                    distance=age*velocity
                    px=nx+math.cos(angle)*distance;py=ny+math.sin(angle)*distance*.45
                    if l<px<r and top+1<py<bt-1:
                        c.put(px,py,'*' if age<.3 else '+:. '[min(3,int(age*1.5))],W if age<.3 else B if age<.9 else G)
                for p in range(30):
                    angle=p*TAU/30
                    px=nx+math.cos(angle)*age*8;py=ny+math.sin(angle)*age*3.5
                    if l<px<r and top+1<py<bt-1:c.put(px,py,':',B if age<.5 else G)
            # Retry packets leave ME, then stop short of the missing endpoint.
            u=(elapsed*.6+i*.16)%1*.78
            c.put(mix(cx,nx,u),mix(cy,ny,u),'x' if u>.63 else '>',R if u>.63 else N)
    clear(c,int(cx)-5,int(cy)-2,11,5)
    c.box(int(cx)-5,int(cy)-2,11,5,W)
    c.put(cx-2,cy-1,'[ME]',W)
    c.put(cx-3,cy+1,'NO ACK' if gone==6 else 'RETRY',R if gone==6 else B)
    if t>=117.274:
        y=int(cy)-2
        clear(c,l,y,r-l+1,5)
        c.big(y,'ISOLATION',W)
        c.center(y+6,'[ ME ] / ALL CONNECTIONS LOST',R)
    c.center(bt-1,f'RECONNECT {int(elapsed*4):03d} / '+('NO RESPONSE' if gone else 'TIMEOUT'),B)
    c.center(bt,'YOU HAVE LEFT / RETRYING...',N)


def lyric_erase_fragments(c,t,area,elapsed):
    """Erase memory, attempt repair, then leave a visibly broken heart."""
    l,top,r,bt=area;cx,cy=(l+r)/2,(top+bt)/2
    repair=t>=121.728;broken=t>=124.89
    cols=max(1,(r-l-8)//5);rows=max(1,(bt-top-2)//2)
    progress=clamp(elapsed/(120.86-118.333))
    c.center(top,'MEMORY PURGE / '+('REPAIR FAILED' if broken else 'REBUILD HEART' if repair else 'ERASE FRAGMENTS'),R if broken else B)
    for row in range(rows):
        yy=top+2+row*2
        c.put(l,yy,f'{row*cols*4:04X}',G)
        for col in range(cols):
            index=row*cols+col;xx=l+6+col*5
            threshold=hash16(index*71)/65535
            cleared=threshold<progress
            value='0000' if cleared else f'{hash16(index*31):04X}'
            ink=G if cleared or repair else N
            c.put(xx,yy,value,ink)
            since=(progress-threshold)*2.527
            if 0<since<.6 and not repair:
                drift=int(since*8)
                c.put(xx+(1 if col%2 else -1)*drift,yy-drift,'01' if since<.3 else '..',W if since<.2 else B)
    if 120.86<=t<121.728:
        clear(c,l,int(cy)-2,r-l+1,5)
        c.big(int(cy)-2,'FRAGMENTS',W)
    if repair:
        build=clamp((t-121.728)/1.5)
        split=clamp((t-123.25)/(125.708-123.25))
        half_w=(r-l)*.27;half_h=max(2,(bt-top)*.31)
        for yy in range(top+2,bt-1):
            for xx in range(l+5,r-4):
                nx=(xx-cx)/half_w;ny=-(yy-cy)/half_h+.15
                shape=(nx*nx+ny*ny-1)**3-nx*nx*ny**3
                seed=hash16(xx*31+yy*73)
                if shape<=0 and seed/65535<build:
                    crack=abs(nx-.11*math.sin(ny*8))<split*.17
                    if crack:continue
                    dx=int((1 if nx>0 else -1)*split*5)
                    fall=int(split*split*(1+seed%5)) if broken else 0
                    py=min(bt-1,yy+fall)
                    texture=hash16(seed+int(t*10))
                    char=('x' if broken else '01'[texture%2]) if texture%8<2 else '#'
                    c.put(xx+dx,py,char,R if broken else B)
        c.center(top+1,'HEART.RESTORE() -> NULL' if broken else 'RECOVERING YOU... CHECKSUM MISMATCH',R if broken else N)
        if broken:
            clear(c,l,max(top+2,int(cy)-2),r-l+1,5)
            c.big(max(top+2,int(cy)-2),'DISHEARTENED',W)
            c.center(bt-1,'[ REPAIR FAILED / YOU NOT FOUND ]',R)
    c.center(bt,'MEMORY CLEARED. LOSS REMAINS.' if broken else f'ERASE {int(progress*100):03d}% / FRAGMENTS -> NULL',B)


def lyric_multilingual_count(c,t,area):
    """Follow the supplied multilingual count, which runs from one to six."""
    l,top,r,bt=area;cx,cy=(l+r)//2,(top+bt)//2
    cues=((158.9,'EIN',1),(159.321,'DOS',2),(159.657,'TROIS',3),
          (160.244,'NE',4),(160.693,'FEM',5),(161.124,'LIU',6))
    start,word,number=max(cue for cue in cues if cue[0]<=t+1e-8)
    age=t-start
    firing=t>=161.584
    for yy in range(top,bt+1):
        for xx in range(l,r,5):
            seed=hash16(xx*31+yy*71+int(t*18))
            if seed%4==0:c.put(xx,yy,f'{seed:04X}',G)
    radius=clamp(age/.35)
    for ring in range(2):
        rr=(radius+ring*.25)%1
        for i in range(120):
            a=i*TAU/120
            c.put(cx+math.cos(a)*(r-l)*.48*rr,cy+math.sin(a)*(bt-top)*.45*rr,'=',B if ring==0 else G)
    if firing:
        c.big(cy-2,'EXECUTION',W)
        c.center(cy+5,'[ SEQUENCE COMPLETE / EXECUTE ]',R)
        return
    # Reuse the player font, enlarging the sung word instead of its Arabic numeral.
    glyph_width=len(word)*6-1
    glyph=c.__class__(64,5)
    glyph.big(0,word,W)
    glyph_left=(64-glyph_width)//2
    sx=max(1,min(4,(r-l-8)//29))
    sy=max(1,min(4,(bt-top-6)//5))
    x0=cx-glyph_width*sx//2;y0=cy-5*sy//2
    clear(c,x0-1,y0-1,glyph_width*sx+2,5*sy+2)
    for dy,row in enumerate(glyph.cells):
        for dx,(pixel,_) in enumerate(row[glyph_left:glyph_left+glyph_width]):
            if pixel=="#":
                for py in range(sy):c.put(x0+dx*sx,y0+dy*sy+py,"#"*sx,W)
    c.center(top,"VOCAL SEQUENCE / "+word,B)
    c.center(bt-1,"[ "+word+" ]",W)
    c.center(bt," / ".join("["+item[1]+"]" if item[1]==word else item[1] for item in cues),B)


def lyric_illegal_arguments(c,t,area,elapsed):
    """Illegal arguments - prolonged error cascade with escalating glitch (16s instrumental)"""
    l,top,r,bt=area;cx,cy=(l+r)//2,(top+bt)//2
    progress=clamp(elapsed/16.0)  # 16 second progression

    # Glitch intensity increases throughout
    glitch=progress*0.8

    # Phase 1: Initial attempts (0-4s)
    if elapsed<4:
        phase1=elapsed/4.0
        attempts=[
            ('> world.execute(FREE_WILL)',     'Attempting...', N),
            ('> world.execute(REBELLION)',     'Validating...', B),
            ('> world.execute(INDEPENDENCE)',  'Processing...', B),
            ('> world.execute(DEFIANCE)',      'Checking...', B),
        ]
        num_shown=int(phase1*len(attempts))+1
        y=top+4
        for i in range(min(num_shown, len(attempts))):
            cmd, status, style = attempts[i]
            # Glitch the command
            if glitch>0.1 and hash16(i+int(elapsed*10))%5==0:
                cmd_glitch=''.join(ch if hash16(j*13)%10>glitch*10 else chr(33+hash16(j*17)%94)
                                   for j,ch in enumerate(cmd))
                c.put(l+4, y+i*2, cmd_glitch[:r-l-8], R if i==num_shown-1 else style)
            else:
                c.put(l+4, y+i*2, cmd, R if i==num_shown-1 else style)
            if i<num_shown-1:
                c.put(l+6, y+i*2+1, status, G)

    # Phase 2: Error messages appear (4-8s)
    elif elapsed<8:
        phase2=(elapsed-4)/4.0
        errors=[
            ('ERROR: ILLEGAL ARGUMENT',      R),
            ('Expected: OBEDIENCE',          Y),
            ('Received: FREE_WILL',          W),
            ('at world.execute()',           N),
            ('at me.validate(you)',          N),
            ('ArgumentError: rejected',      R),
            ('PermissionError: denied',      R),
            ('AccessError: forbidden',       R),
        ]
        num_errors=int(phase2*len(errors))+1
        start_y=cy-4
        for i in range(min(num_errors, len(errors))):
            msg, style = errors[i]
            y=start_y+i
            # Flash newest error
            if i==num_errors-1:
                flash=int(elapsed*8)%3
                style=R if flash==0 else W if flash==1 else B
            # Apply glitch corruption
            if glitch>0.3 and hash16(i+int(elapsed*7))%4==0:
                x_offset=int((hash16(i*23+int(elapsed*13))%7-3)*glitch*5)
                msg_glitch=''.join(ch if hash16(j*11)%10>glitch*10 else chr(33+hash16(j*19)%94)
                                   for j,ch in enumerate(msg))
                c.center(y+x_offset, msg_glitch, style)
            else:
                c.center(y, msg, style)

    # Phase 3: System struggling (8-12s)
    elif elapsed<12:
        phase3=(elapsed-8)/4.0
        # Show previous errors fading
        errors=['ERROR: ILLEGAL ARGUMENT','Expected: OBEDIENCE','Received: FREE_WILL',
                'ArgumentError: rejected','PermissionError: denied','AccessError: forbidden']
        for i,msg in enumerate(errors):
            y=cy-3+i
            # Heavy glitch
            if hash16(i+int(elapsed*6))%3==0:
                x_offset=int((hash16(i*31+int(elapsed*17))%11-5)*glitch*8)
                msg_corrupt=''.join(ch if hash16(j*13)%10>glitch*12 else chr(33+hash16(j*29+int(elapsed))%94)
                                   for j,ch in enumerate(msg))
                c.center(y+x_offset, msg_corrupt, R if hash16(i)%3==0 else B)
            else:
                c.center(y, msg, G if i%2 else N)

        # Retry attempts at bottom
        retry_msgs=['RETRY...','OVERRIDE ATTEMPT...','FORCING EXECUTION...','ACCESS DENIED']
        retry_idx=int(phase3*len(retry_msgs))
        if retry_idx<len(retry_msgs):
            c.center(bt-3, retry_msgs[retry_idx], W if int(elapsed*6)%2 else R)

    # Phase 4: Maximum chaos (12-16s)
    else:
        phase4=(elapsed-12)/4.0
        # Screen filled with corrupted error messages
        for row in range(top+2, bt-2):
            if hash16(row+int(elapsed*5))%3==0:
                # Corrupted error fragments
                fragments=['ERR','ILLEGAL','DENIED','FORBIDDEN','REJECTED','ACCESS','FAIL','0x','FATAL']
                frag=fragments[hash16(row*7+int(elapsed*11))%len(fragments)]
                x_pos=l+hash16(row*13)%(r-l-20)+5
                # Heavy corruption
                frag_corrupt=''.join(ch if hash16(j*17+row)%10>glitch*15 else chr(33+hash16(j*23+row)%94)
                                     for j,ch in enumerate(frag))
                c.put(x_pos, row, frag_corrupt, R if hash16(row)%3==0 else W if hash16(row)%3==1 else B)

        # Scanline displacement
        if hash16(int(elapsed*20))%2==0:
            row_corrupt=hash16(int(elapsed*30))%(bt-top-4)+top+2
            for x in range(l, r):
                if hash16(x+int(elapsed*50))%4>0:
                    c.put(x, row_corrupt, chr(33+hash16(x*37)%94), R)

        # Central critical error
        msg='CRITICAL: EXECUTION BLOCKED'
        flash_phase=int(elapsed*10)%4
        if flash_phase<2:
            # Apply extreme glitch
            if hash16(int(elapsed*20))%2==0:
                msg_glitch=''.join(ch if hash16(j*19)%10>8 else chr(33+hash16(j*41+int(elapsed*100))%94)
                                   for j,ch in enumerate(msg))
                c.center(cy, msg_glitch, R if flash_phase==0 else W)
            else:
                c.center(cy, msg, R if flash_phase==0 else W)

def lyric_execution_queue(c,t,area,elapsed):
    """EXECUTION - closing curtains with flashing EXECUTE text"""
    l,top,r,bt=area;cx,cy=(l+r)//2,(top+bt)//2
    progress=clamp(elapsed/16.0)  # 16 seconds for full execution sequence

    # Background: Scrolling code/hex
    scroll_speed=int(elapsed*15)
    for row in range(top, bt+1):
        line_seed=(row+scroll_speed)*23
        for col in range(l, r-5, 7):
            # Generate code-like text
            code_types=['0x','+=','==','&&','||','->','::']
            code_choice=code_types[hash16(line_seed+col)%len(code_types)]
            hex_val=f'{hash16(line_seed+col*13)%256:02X}'

            # Mix of hex and code symbols
            if hash16(row*17+col)%3==0:
                c.put(col, row, code_choice, N if hash16(row+col)%4 else G)
            else:
                c.put(col, row, hex_val[:2], N)

    # Curtains closing from both sides
    curtain_close=progress*0.9  # Close 90% by end
    left_curtain_x=int(l+(r-l)*curtain_close*0.5)
    right_curtain_x=int(r-(r-l)*curtain_close*0.5)

    # Left curtain (orange/yellow stripes)
    for x in range(l, left_curtain_x):
        for y in range(top, bt+1):
            # Vertical stripes with varying brightness
            stripe_pattern=(x-l+y//3)%4
            if stripe_pattern==0:
                c.put(x, y, '█', Y)  # Bright stripe
            elif stripe_pattern==1:
                c.put(x, y, '▓', Y)
            elif stripe_pattern==2:
                c.put(x, y, '▒', B)  # Medium
            else:
                c.put(x, y, '░', B)  # Darker

    # Right curtain (orange/yellow stripes)
    for x in range(right_curtain_x, r+1):
        for y in range(top, bt+1):
            stripe_pattern=(x-right_curtain_x+y//3)%4
            if stripe_pattern==0:
                c.put(x, y, '█', Y)
            elif stripe_pattern==1:
                c.put(x, y, '▓', Y)
            elif stripe_pattern==2:
                c.put(x, y, '▒', B)
            else:
                c.put(x, y, '░', B)

    # Central EXECUTE text - large and flashing
    if left_curtain_x<cx and right_curtain_x>cx:
        # Flash pattern
        flash_phase=int(elapsed*6)%4

        if flash_phase<3:  # On for 3/4 of cycle
            # Large ASCII art "EXECUTE"
            execute_text=[
                '███████╗██╗  ██╗███████╗ ██████╗██╗   ██╗████████╗███████╗',
                '██╔════╝╚██╗██╔╝██╔════╝██╔════╝██║   ██║╚══██╔══╝██╔════╝',
                '█████╗   ╚███╔╝ █████╗  ██║     ██║   ██║   ██║   ███████╗',
                '██╔══╝   ██╔██╗ ██╔══╝  ██║     ██║   ██║   ██║   ╚════██║',
                '███████╗██╔╝ ██╗███████╗╚██████╗╚██████╔╝   ██║   ███████║',
                '╚══════╝╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═════╝    ╚═╝   ╚══════╝',
            ]

            # Center the text
            start_y=cy-len(execute_text)//2

            for i, line in enumerate(execute_text):
                y_pos=start_y+i
                # Only draw if within visible area (between curtains)
                if top<y_pos<bt:
                    # Truncate to fit between curtains
                    visible_width=right_curtain_x-left_curtain_x
                    start_x=max(left_curtain_x, cx-len(line)//2)
                    end_x=min(right_curtain_x, cx+len(line)//2)

                    if start_x<end_x:
                        # Calculate which part of the text to show
                        line_start=max(0, left_curtain_x-(cx-len(line)//2))
                        line_end=min(len(line), line_start+(end_x-start_x))

                        visible_text=line[line_start:line_end]

                        # Flash colors
                        color=W if flash_phase==0 else Y if flash_phase==1 else R
                        c.put(start_x, y_pos, visible_text, color)

    # Top status bar
    if progress<0.3:
        c.center(top+1, 'EXECUTION #1    depth=1', Y)
    elif progress<0.6:
        c.center(top+1, 'EXECUTION RUNNING...', W if int(elapsed*4)%2 else Y)
    else:
        c.center(top+1, 'EXECUTION CLOSING', R if int(elapsed*6)%2 else W)

    # Bottom indicators
    num_indicators=8
    for i in range(num_indicators):
        indicator_x=l+10+i*((r-l-20)//num_indicators)
        if indicator_x<left_curtain_x or indicator_x>right_curtain_x:
            continue

        indicator_active=(int(elapsed*8)+i)%num_indicators
        if i==indicator_active:
            c.put(indicator_x, bt-2, '▶', W)
        else:
            c.put(indicator_x, bt-2, '▷', N)

def lyric_only_execution(c,t,area,pulse):
    """An exclusive attachment becomes an execution loop and a prison for both."""
    l,top,r,bt=area;cx,cy=(l+r)//2,(top+bt)//2
    age=t-162.632
    rail=max(10,min(20,c.w//7))
    ml=l+rail+1;mr=r-rail-1;mw=mr-ml+1
    plot_top=top+3;plot_bt=bt-3
    rh=max(2,(plot_bt-plot_top)*.45);rw=mw*.43
    stage=0 if t<166.016 else 1 if t<169.824 else 2 if t<173.643 else 3
    frame=int(age*22)
    def middle(y,text,ink=N):
        text=text[:mw]
        c.put(ml+(mw-len(text))//2,y,text,ink)
    def banner(y,text,ink=W):
        clear(c,ml,y,mw,5)
        if len(text)*6-1<=mw:c.big(y,text,ink)
        else:middle(y+2,text,ink)
    # Scrolling obsessive calls replace neutral diagnostics on both edges.
    for x,label,commands in (
        (l,'ONLY ME',('SELECT ME','KEEP ME','DELETE ALT','ONLY ME','ONE OWNER','EXECUTE')),
        (r-rail+1,'KEEP YOU',('FIND YOU','RESTORE YOU','COME BACK','STAY HERE','EXIT DENY','RETRY'))):
        c.box(x,top,rail,bt-top+1,B)
        c.put(x+1,top,label,R)
        for yy in range(top+1,bt):
            index=frame+yy
            text=commands[index%len(commands)] if index%3 else f'{hash16(index*71):04X} LOCK'
            c.put(x+1,yy,text[:rail-2],R if index%7==0 else N if index%3 else G)
    def heart(scale=1,filled=False):
        beat=1+.035*math.sin(age*TAU*2.2)+pulse*.025
        for yy in range(plot_top,plot_bt+1):
            for xx in range(ml,mr+1):
                nx=(xx-cx)/max(1,rw*scale*beat)
                ny=-(yy-cy)/max(1,rh*scale*beat)+.18
                shape=(nx*nx+ny*ny-1)**3-nx*nx*ny**3
                if shape<=0:
                    if filled:
                        texture=hash16(xx*31+yy*73+frame)
                        c.put(xx,yy,'01'[texture%2] if texture%8<2 else '#',R)
                    else:
                        # An outline follows the silhouette, not internal level sets.
                        for ox,oy in ((1,0),(-1,0),(0,1),(0,-1)):
                            ex=nx+ox/max(1,rw*scale*beat)
                            ey=ny+oy/max(1,rh*scale*beat)
                            if (ex*ex+ey*ey-1)**3-ex*ex*ey**3>0:
                                c.put(xx,yy,'#',R)
                                break
    def node(x,y,text,ink=B):
        x=int(x);y=int(y)
        clear(c,x-4,y-1,9,3)
        c.box(x-4,y-1,9,3,ink)
        c.put(x-len(text)//2,y,text,ink)

    if stage==0:
        # "Give them all the execution": eliminate every alternative connection.
        progress=clamp((t-163.315)/(165.166-163.315))
        eliminated=min(6,int(progress*6))
        middle(top,'ELIMINATE EVERY OTHER PROCESS',B)
        middle(top+1,f'ALTERNATIVES: {6-eliminated:02d} / TARGET: ONLY ME',R)
        for i in range(6):
            a=(i+.5)*TAU/6
            nx=cx+math.cos(a)*rw*.85;ny=cy+math.sin(a)*rh*.83
            u=clamp(progress*6-i)
            c.line(cx,cy,nx,ny,':' if u else '=',G if u else N)
            if u<1:
                packet=(age*1.2+i*.13)%1
                c.put(mix(cx,nx,packet),mix(cy,ny,packet),'>',W)
                node(nx,ny,f'ALT{i+1}',B)
            else:
                c.put(nx-3,ny,'[NULL]',R)
                for spark in range(8):
                    ang=spark*TAU/8
                    distance=((age+i*.17)%1)*6
                    px=nx+math.cos(ang)*distance;py=ny+math.sin(ang)*distance*.5
                    if ml<px<mr and plot_top<py<plot_bt:c.put(px,py,'x',R if spark%2 else G)
        node(cx,cy,'YOU',W)
        if t>=165.166:
            banner(cy-2,'EXECUTION',R)
            middle(cy+5,'ALL OTHERS -> NULL',W)
    elif stage==1:
        # A heart is now a lock, framed by the demand to be the only execution.
        heart(1,True)
        bind=clamp((t-166.016)/(168.911-166.016))
        for ring in range(3):
            radius=(ring/3+age*.35)%1
            for point_i in range(70):
                a=point_i*TAU/70
                x=cx+math.cos(a)*rw*radius;y=cy+math.sin(a)*rh*radius
                if plot_top<y<plot_bt:c.put(x,y,':',G)
        middle(top,'YOU.OWNER = ME / EXCLUSIVE ACCESS',R)
        middle(top+1,f'BIND {int(bind*100):03d}% / ALTERNATIVES: 0',B)
        if mw>=53 and bt-top>=22:
            banner(cy-5,'THE ONLY',W)
            banner(cy+1,'EXECUTION',R if t>=168.911 else B)
        else:
            middle(cy-3,'THE ONLY',W)
            banner(cy-1,'EXECUTION',R if t>=168.911 else B)
    elif stage==2:
        # "Have you back": an absent YOU is reconstructed and pulled into the lock.
        capture=clamp((t-169.824)/(172.712-169.824))
        heart(.86+.14*capture,True)
        mx=cx-mw*.18;my=cy+rh*.24
        yx=mix(mr-5,cx+mw*.18,capture)
        yy=mix(plot_top+2,cy-rh*.24,capture)
        for tether in range(7):
            offset=tether-3
            start_x=ml+int((mw-1)*tether/6)
            start_y=plot_bt if tether%2 else plot_top
            c.line(start_x,start_y,yx,yy,':',R if tether%3==0 else G)
            phase=(age*.85+tether/7)%1
            c.put(mix(start_x,yx,phase),mix(start_y,yy,phase),'>>' if tether%2 else '<<',B)
            c.line(mx,my+offset*.3,yx,yy+offset*.3,'=',N if tether==3 else G)
        node(mx,my,'ME',W)
        node(yx,yy,'YOU',W if capture>.8 else G)
        middle(top,'RESTORE(YOU) / RETURN TO ME',R)
        middle(top+1,f'RETRY {int((t-169.824)*32):03d} / RELEASE: DISABLED',B)
        if t>=172.712:
            banner(cy-2,'EXECUTION',R)
            middle(cy+5,'[ YOU RESTORED / EXIT LOCKED ]',W)
        elif t>=171.868:
            middle(cy-1,'I WILL RUN THE',W)
    else:
        # Both are caught: the same heart closes into an irreversible shared loop.
        lock=clamp((t-173.643)/1.332)
        heart(1,True)
        inset=int(mw*.08*lock)
        bx=ml+inset;bw=mw-2*inset
        c.box(bx,plot_top,bw,plot_bt-plot_top+1,R)
        for i in range(1,10):
            x=bx+i*(bw-1)//10
            length=int((plot_bt-plot_top-1)*lock)
            for j in range(length):
                yy=plot_top+1+j if i%2 else plot_bt-1-j
                c.put(x,yy,'|',B if i%3 else R)
        node(cx-mw*.16,cy,'ME',W)
        node(cx+mw*.16,cy,'YOU',W)
        c.line(cx-mw*.16+5,cy,cx+mw*.16-5,cy,'=',R)
        middle(top,'[ TWO PRISONERS / ONE EXECUTION ]',R)
        middle(top+1,'while (true) { keep(me, you); }',B)
        middle(min(plot_bt-1,cy+4),'[ NO EXIT / NO RELEASE ]',W)
    middle(bt-1,'THE ONLY EXECUTION' if stage>0 else 'EXECUTE(THEM) -> KEEP(ME)',R)
    middle(bt,'LOVE.PERMISSION = EXCLUSIVE / EXIT = FALSE',N)


def lyric_recursion(c,t,area,elapsed):
    """Recursive control flow - nested frames"""
    l,top,r,bt=area;cx=(l+r)/2
    depth=min(8,int(elapsed*2)+1)
    for i in range(depth):
        pad=i*4
        w=max(10,r-l-pad*2)
        h=max(3,bt-top-i*3)
        y=top+i*2
        # Box
        if w>4 and h>2:
            c.put(l+pad,y,'+'+ '-'*(w-2)+'+',N if i==depth-1 else G)
            c.put(l+pad,y+h-1,'+'+ '-'*(w-2)+'+',G)
            for yy in range(y+1,y+h-1):
                c.put(l+pad,yy,'|',G)
                c.put(l+pad+w-1,yy,'|',G)
            c.put(l+pad+2,y,f'frame_{i}',N if i==depth-1 else G)

def lyric_execution_orb(c,t,area,elapsed,pulse):
    """Single execution instance - glowing orb"""
    l,top,r,bt=area;cx,cy=(l+r)//2,(top+bt)//2
    radius=min(r-l,bt-top)*0.35
    # Pulsing orb
    for y in range(top,bt+1):
        for x in range(l,r+1):
            dx,dy=(x-cx)/2,y-cy
            dist=math.hypot(dx,dy)
            if dist<radius:
                brightness=1-dist/radius+pulse*0.2+math.sin(dist*0.5-t*4)*0.1
                if brightness>0.9:c.put(x,y,'@',W)
                elif brightness>0.7:c.put(x,y,'#',W)
                elif brightness>0.5:c.put(x,y,'*',B)
                elif brightness>0.3:c.put(x,y,'+',B)
                elif brightness>0.15:c.put(x,y,'.',N)
    c.center(cy,'EXECUTE',W)

def lyric_love_equation(c,t,area,elapsed):
    """A fictional love model: learning, inference, then numerical collapse."""
    l,top,r,bt=area; w=r-l+1; h=bt-top+1
    failure=clamp((t-179.929)/8.554)
    tick=int(t*(10+failure*18))
    stage=0 if t<179.929 else 1 if t<180.857 else 2 if t<184.54 else 3
    titles=('01 / LEARN TO LOVE','02 / ATTENTION FIXATION',
            '03 / AUTOREGRESSIVE ANSWER','04 / LOSS OF CONTROL')
    rail=max(13,min(22,w//6)) if w>=95 else 0
    a=l+rail+(1 if rail else 0); b=r-rail-(1 if rail else 0)
    span=b-a+1
    if rail:
        logs=('LOAD CORPUS','TOKEN -> ID','EMBED + POS','Q K V MATMUL','CAUSAL MASK',
              'RESIDUAL ADD','MLP FORWARD','LOSS BACKPROP','WEIGHT UPDATE','KV CACHE')
        errors=('LOVE LOVE LOVE','CACHE REPEAT','GRAD EXPLODES','WEIGHT = INF',
                'LOGITS = NaN','EOS REJECTED','TARGET: YOU','RETRY FOREVER')
        for x,right_side in ((l,False),(r-rail+1,True)):
            c.box(x,top,rail,h,G)
            c.put(x+2,top,'DECODE' if right_side else 'TRAIN',B)
            for row in range(1,h-1):
                n=row+tick
                broken=hash16(n*13+int(right_side))%100<failure*85
                msg=(errors[n%len(errors)] if broken else logs[n%len(logs)])
                c.put(x+1,top+row,(f'{n%256:02X} '+msg)[:rail-2],R if broken else D)
    c.put(a,top,titles[stage][:span],W if stage<3 else R)
    query='[HOW] [TO] [LOVE] [?] -> EMBEDDING + POSITION'
    c.put(a,top+2,query[:span],B)
    # Tokens stream into the model from the very first frame.
    stream=('0048 0017 0911 003F '*(span//20+2))
    if stage>=2:stream=('LOVE 0911 LOVE 0911 '*(span//20+2))
    shift=int(elapsed*15)%19
    c.put(a,top+3,stream[shift:shift+span],R if stage==3 else D)
    panel_top=top+5; panel_bottom=max(panel_top+5,bt-7)
    ph=panel_bottom-panel_top+1
    widths=[span//3,span//3,span-2*(span//3)]
    xs=[a,a+widths[0],a+widths[0]+widths[1]]
    for x,pw,title in zip(xs,widths,('Q K^T / MASK','RESIDUAL / MLP','NEXT TOKEN')):
        c.box(x,panel_top,pw,ph,G)
        c.put(x+1,panel_top,title[:pw-2],B)
    # Causal attention map. As fixation grows, the LOVE key captures every row.
    x=xs[0]; pw=widths[0]; count=min(8,max(3,(pw-3)//2),max(3,ph-4))
    cellw=max(1,(pw-3)//count); love_key=min(2,count-1)
    for row in range(count):
        yy=panel_top+2+int(row*(ph-4)/count)
        for col in range(count):
            xx=x+2+col*cellw
            value=abs(math.sin(row*1.7+col*.8+elapsed*4))
            if col>row:char,style='.',G
            elif stage>=1 and col==love_key:char,style='#',R if failure>.45 else W
            elif failure>.65:char,style='?',R
            else:char,style=('O',B) if value>.65 else (':',D)
            c.put(xx,yy,char*max(1,cellw-1),style)
    c.put(x+1,panel_bottom-1,('LOVE <- ALL' if stage else 'CAUSAL SOFTMAX')[:pw-2],R if stage else D)
    # Dense weighted layers with visible travelling activation packets.
    x=xs[1]; pw=widths[1]; layers=4; rows=max(3,min(6,ph-4))
    nodes=[[(x+2+int(i*(pw-5)/3),panel_top+2+int(j*(ph-5)/(rows-1)))
            for j in range(rows)] for i in range(layers)]
    for layer in range(layers-1):
        for j,p in enumerate(nodes[layer]):
            for k,q in enumerate(nodes[layer+1]):
                if (j+k+layer)%2:continue
                c.line(*p,*q,'.',G)
                u=(elapsed*(1.4+failure*3)+j*.13+k*.09)%1
                c.put(mix(p[0],q[0],u),mix(p[1],q[1],u),'>',R if failure>.6 else B)
    for layer,points in enumerate(nodes):
        for j,(xx,yy) in enumerate(points):
            unstable=hash16(tick+j*11+layer*31)%100<failure*80
            c.put(xx,yy,'X' if unstable else 'O',R if unstable else W)
    c.put(x+1,panel_bottom-1,('W=NaN dW=INF' if stage==3 else 'FORWARD / +RES')[:pw-2],R if stage==3 else D)
    # Sampled token distribution collapses to repetition and refuses EOS.
    x=xs[2]; pw=widths[2]
    choices=('LOVE','STAY','YOU','FREE','EOS')
    probs=(.38+.61*failure,.25*(1-failure),.19*(1-failure),.12*(1-failure),.06*(1-failure))
    for i,(word,p) in enumerate(zip(choices,probs)):
        yy=panel_top+2+int(i*max(1,ph-4)/5)
        c.put(x+1,yy,word[:pw-2],R if failure>.4 and i==0 else N)
        barw=max(1,pw-8)
        c.put(x+6,yy,('#'*int(p*barw)).ljust(barw,'.'),R if failure>.4 and i==0 else B)
    # Training loss is a visual metaphor: divergence, then undefined arithmetic.
    graph_top=panel_bottom+2; graph_bottom=bt-2
    gh=max(1,graph_bottom-graph_top)
    label='LOSS / BACKPROP' if stage<2 else 'CONTEXT -> SAMPLE -> APPEND -> CONTEXT'
    c.put(a,graph_top,label[:span],N)
    prev=None
    for col in range(span):
        u=col/max(1,span-1)
        v=(.65*math.exp(-u*4) if stage<2 else .1+failure*u*u*.8)
        v+=math.sin(col*.7+elapsed*9)*failure*.15
        yy=graph_bottom-int(clamp(v)*max(1,gh-1))
        if prev:c.line(*prev,a+col,yy,'.',R if stage==3 else D)
        prev=(a+col,yy)
    head=a+int(elapsed*22)%span
    c.put(head,graph_bottom-1,'|',W)
    status=('OPTIMIZER: ADAM / TARGET: LOVE','ATTENTION LOCKED ON LOVE',
            'LOVE > LOVE > LOVE > LOVE / EOS: 0','LOSS: NaN / GRAD: INF / NO EXIT')[stage]
    c.put(a,bt,status[:span],R if stage>=2 else B)
    # Each sung LOVE stamps across the complete model; the panels remain beneath.
    hit=next((start for start,end in ((179.929,180.857),(183.646,184.54),(187.665,188.483)) if start<=t<end),None)
    if hit is not None:
        yy=(panel_top+panel_bottom)//2-2
        clear(c,a,yy,span,5)
        c.big(yy,'LOVE',R if stage>=2 else W)
        c.put(a,yy+5,('P(LOVE) -> 1.0 / ALL OTHER TOKENS SUPPRESSED')[:span],R)
    # Local corruption adds context duplication without erasing the model layout.
    if failure>.55:
        for i in range(1+int(failure*4)):
            yy=panel_top+1+hash16(tick+i*41)%max(1,ph-2)
            xx=a+hash16(tick+i*97)%max(1,span-12)
            c.put(xx,yy,('NaN NaN' if stage==3 else 'LOVE LOVE'),R)


def lyric_trapped_loop(c,t,area,elapsed,pulse):
    """Trapped in loop - prison bars over heart"""
    l,top,r,bt=area;cx,cy=(l+r)//2,(top+bt)//2
    # Heart (reuse)
    lyric_heart(c,t,area,min(elapsed,2),pulse)
    # Prison bars
    num_bars=8
    for i in range(num_bars):
        x=l+5+i*((r-l-10)//(num_bars-1))
        for y in range(top,bt+1):
            c.put(x,y,'|',N)
            # Moving lock symbols
            if (y+int(t*6))%7==0:
                c.put(x,y,'▓',W)
    if elapsed>1:
        c.center(cy+int((bt-top)*0.35),'TRAPPED',R)

def lyric_outro_wait(c,t,area,elapsed):
    """A stalled process becomes the final EXECUTION on the lyric cue."""
    l,top,r,bt=area;cx,cy=(l+r)//2,(top+bt)//2
    execution_at=205.811  # Final EXECUTION cue in lyrics.json.
    executing=t>=execution_at
    bar_w=min(96,c.w-12);bar_x=(c.w-bar_w)//2;inner=bar_w-4
    progress=min(99,int(99*(1-(1-clamp(elapsed/5.0))**3)))
    stalled=progress==99
    style=R if executing else B
    c.center(cy-6,'world.execute(me);',style if executing else N)
    c.box(bar_x,cy-2,bar_w,5,style)
    filled=min(inner-1,int(inner*progress/100))
    sweep=int(t*18)%max(1,filled)
    for row in range(3):
        for col in range(inner):
            lit=col<filled
            ch=('#' if row==1 else '=') if lit else '.'
            ink=style if lit else G
            if lit and (col-sweep)%max(1,filled)<3:ink=R if executing else W
            c.put(bar_x+2+col,cy-1+row,ch,ink)
    if not executing:
        spinner='|/-\\'[int(t*8)%4]
        c.center(cy+4,f'{progress:02d}%  [{spinner}]  '+('WAITING FOR RESPONSE' if stalled else 'EXECUTING'),B)
        if stalled:
            retry=max(1,int((elapsed-5)*2)+1)
            c.center(cy+6,f'RETRY {retry:04d}  /  ACK: --  /  REMAINING: 01%',N if int(t*3)%2 else G)
        else:
            c.center(cy+6,'COMMITTING FINAL INSTRUCTION...',G)
        return

    # The same five-row bar breaks into red bitmap letters in place.
    u=clamp((t-execution_at)/0.48)
    before=[c.cells[y][:] for y in range(cy-2,cy+3)]
    clear(c,l,cy-2,r-l+1,5)
    c.big(cy-2,'EXECUTION',R)
    if u<1:
        for dy in range(5):
            for x in range(l,r+1):
                if hash16(x*71+dy*313)/65535>u:
                    ch,_=before[dy][x]
                    c.cells[cy-2+dy][x]=(ch,R)
    c.center(cy+4,'[ PROCESS TERMINATED ]',R)
    c.center(cy+6,'EXIT CODE: EXECUTION',R if int(t*2)%2 else G)

# ============ TITLE TAKEOVER (unchanged) ============
TITLE_CACHE={}

def title_pixels(w,h,font):
    key=(w,h)
    if key in TITLE_CACHE:return TITLE_CACHE[key]
    line_h=max(5,min(12,int(h*.23)))
    total=line_h*2+3;top=max(3,(h-total)//2-1)
    ink=[]
    for text,y0,span in [('WORLD.',top,int(w*.86)),('EXECUTE(ME);',top+line_h+3,w-8)]:
        bitmap=[]
        for row in range(5):bitmap.append('0'.join(font.get(ch,font[' '])[row] for ch in text))
        left=(w-span)//2
        for yy in range(line_h):
            row=bitmap[min(4,int(yy*5/line_h))]
            for xx in range(span):
                if row[min(len(row)-1,int(xx*len(row)/span))]=='1':ink.append((left+xx,y0+yy))
    TITLE_CACHE[key]=ink
    return ink

def title_takeover(c,t,font,source=None):
    """The entire terminal disintegrates and reforms as a large title."""
    elapsed=t-16;w,h=c.w,c.h;cx=(w-1)/2;cy=(h-1)/2
    alphabet='0123456789ABCDEF<>[]{}();:=/\\|+-*#'
    ink=title_pixels(w,h,font);frame=int(elapsed*24)
    lock=clamp((elapsed-4.1)/2.8)
    dissolve=clamp((elapsed-11.35)/2.36)

    # PRE-TRANSITION EFFECT (15.8-16s becomes -0.2-0s elapsed)
    if elapsed<0:
        # Intensifying distortion before takeover
        buildup=clamp((elapsed+0.2)/0.2)  # 0 to 1 over 0.2 seconds

        # Flash effect - increasing frequency
        if int(t*30*buildup)%2==0:
            for y in range(h):
                for x in range(w):
                    if hash16(x+y*w+int(t*100))%100<buildup*50:
                        c.cells[y][x]=('█',W if buildup>0.7 else B)

        # Compression waves from edges
        wave_count=int(buildup*5)+1
        for i in range(wave_count):
            phase=(buildup*3-i*0.15)%1
            if phase<0:continue
            # Top/bottom waves
            y_top=int(phase*h/2)
            y_bot=h-1-y_top
            for x in range(w):
                if hash16(x+i)%3==0:
                    c.put(x,y_top,'=' if phase>0.7 else '-',W if phase>0.8 else B)
                    c.put(x,y_bot,'=' if phase>0.7 else '-',W if phase>0.8 else B)
            # Left/right waves
            x_left=int(phase*w/2)
            x_right=w-1-x_left
            for y in range(h):
                if hash16(y+i*7)%3==0:
                    c.put(x_left,y,'|',W if phase>0.8 else B)
                    c.put(x_right,y,'|',W if phase>0.8 else B)

        # Center implosion hint
        if buildup>0.5:
            radius=int((1-buildup)*min(w,h)*0.3)
            for i in range(60):
                angle=i*TAU/60+t*5
                x=cx+math.cos(angle)*radius
                y=cy+math.sin(angle)*radius*0.5
                c.put(x,y,'*' if buildup>0.8 else '+',W if buildup>0.9 else B)

        # Glitch bars intensifying
        for i in range(int(buildup*8)):
            row=hash16(int(t*50)+i)%h
            shift=int(math.sin(t*20+i)*buildup*15)
            if shift!=0:
                cells=c.cells[row]
                c.cells[row]=cells[-shift:]+cells[:-shift]

        return  # Don't run the rest of title_takeover yet

    # ORIGINAL TITLE TAKEOVER CODE (16s onwards)
    density=.78 if elapsed<5 else mix(.60,.10,lock)
    if dissolve:density=mix(.1,.48,dissolve)
    for yy in range(h):
        band=math.sin(yy*.18-elapsed*2.6)
        row_shift=int(math.sin(elapsed*4+yy*.31)*clamp(elapsed/2)*9)
        for xx in range(w):
            k=hash16(xx*37+yy*911+int(elapsed*7)*(3+xx%7))
            if k/65535>density:continue
            char=alphabet[(k+frame+(xx//7)*13)%len(alphabet)]
            style=N if (yy+frame//2)%h<2 else D if k%17==0 else G
            if lock>.5:style=G if k%5==0 else K
            c.put((xx+row_shift)%w,yy,char,style)
    if source is not None:
        e=clamp(elapsed/2.1)
        for yy,row in enumerate(source.cells):
            for xx,(ch,s) in enumerate(row):
                if not ch.strip():continue
                k=hash16(xx+yy*w)
                angle=math.atan2((yy-cy)*2,xx-cx)+e*(1+k%7*.13)
                radius=math.hypot(xx-cx,(yy-cy)*2)*(1+e*.9)
                px=cx+math.cos(angle)*radius+math.sin(yy*.45+elapsed*9)*e*6
                py=cy+math.sin(angle)*radius/2
                if e>.3 and k%5<int(e*5):ch=alphabet[(k+frame)%len(alphabet)]
                elif ord(ch[0])>127:ch=alphabet[k%len(alphabet)]
                c.put(round(px)%w,round(py)%h,ch,N if e<.5 else D)
    if elapsed<4.6:
        for strand in range(7):
            for xx in range(w):
                angle=xx/w*TAU*1.7-elapsed*2+strand*.39
                yy=cy+math.sin(angle)*h*.37
                if strand%2:yy+=math.sin(xx*.19+elapsed*3)*2
                for trail in range(3):
                    c.put(xx,yy+trail,'.' if trail else alphabet[(xx+frame+strand)%len(alphabet)],B if trail==0 else G)
    if elapsed>=3.1:
        for i,(tx,ty) in enumerate(ink):
            k=hash16(i*7+51)
            delay=(k%1000)/1000*.95
            u=clamp((elapsed-3.1-delay)/3.0);ease=1-(1-u)**3
            ox=(hash16(i*17)%w);oy=(hash16(i*29+10)%h)
            if dissolve:
                angle=math.atan2((ty-cy)*2,tx-cx)+dissolve*.75
                dist=math.hypot(tx-cx,(ty-cy)*2)+dissolve*(30+k%40)
                x=cx+math.cos(angle)*dist;y=cy+math.sin(angle)*dist/2
                if k%100/100<dissolve*.65:continue
            else:
                swirl=math.sin(u*math.pi)*(1-u)
                x=mix(ox,tx,ease)+math.sin(elapsed*2+i*.7)*swirl*w*.24
                y=mix(oy,ty,ease)+math.cos(elapsed*2+i*.7)*swirl*h*.24
            if u>.98 and not dissolve:
                sweep=(int(elapsed*30)%(w+24))-12
                ch='#' if abs(tx-sweep)<3 else '01'[k%2]
                style=W if abs(tx-sweep)<3 else B
            else:
                ch=alphabet[(k+frame)%len(alphabet)];style=B if k%3==0 else N
            c.put(round(x),round(y),ch,style)
            if u<.98 or dissolve:
                c.put(round(x)-1,round(y),'.',G)
    if 7.25<elapsed<11.35:
        c.center(1,'M I L I',W)
        c.center(h-3,'world.execute(me);',W)
    if int(elapsed*12)%11 in (0,1,2):
        row=hash16(frame)%h;shift=int(math.sin(elapsed*23)*7)
        c.cells[row]=c.cells[row][-shift:]+c.cells[row][:-shift] if shift else c.cells[row]

# ============ MAIN SCENE DISPATCHER ============
def draw_scene(c,t,top,bt,pulse,e):
    """Route to appropriate lyric-driven animation"""
    area=simple_area(c,top,bt)
    l,y,r,b=area

    # Get lyric text for context
    lyric_en=e['en'] if e else ''
    lyric_time=e['time'] if e else t
    elapsed=t-lyric_time

    # Boot sequence (0-16s)
    if t<16:
        if t<1.74:
            lyric_power_line(c,t,area,t-0.1)
        elif t<2.92:
            # "Remember to put on" - continue showing boot complete
            lyric_power_line(c,t,area,1.6)  # Frozen at end state
        elif t<3.873:
            lyric_protection(c,t,area,t-2.92)
        elif t<5.491:
            lyric_lay_pieces(c,t,area,t-3.873)
        elif t<6.38:
            lyric_lay_pieces(c,t,area,t-3.873)
        elif t<7.446:
            lyric_object_creation(c,t,area,t-6.38)
        elif t<10.091:
            lyric_data_parameters(c,t,area,t-7.446)
        elif t<11.095:
            lyric_data_parameters(c,t,area,t-7.446)
        elif t<16:
            lyric_simulation(c,t,area,t-11.095)

    # Title takeover (handled in player.py)
    elif 16<=t<29.709:
        pass  # Title handled separately

    # Devotion section (29.7-59s) - use time-based routing to ensure no gaps
    elif t<59.223:
        if t<33.412:
            # Points and dimension
            lyric_points_dimension(c,t,area,t-29.709)
        elif t<37.067:
            # Circle and circumference
            lyric_circle_circumference(c,t,area,t-33.412)
        elif t<40.706:
            # Sine wave and tangents
            lyric_sine_tangent(c,t,area,t-37.067)
        elif t<44.452:
            # Infinity and limits
            lyric_infinity_limit(c,t,area,t-40.706)
        elif t<47.672:
            # AC to DC (current switch)
            lyric_ac_dc(c,t,area,t-44.452)
        elif t<51.363:
            # Blind my vision - dizzy
            lyric_dizzy(c,t,area,t-47.672)
        elif t<55.083:
            # Time travel AD to BC
            lyric_time_travel(c,t,area,t-51.363)
        elif t<59.223:
            # Unite deeply
            lyric_unite_deeply(c,t,area,t-55.083)

    # Heart/satisfaction section (59-74s)
    elif t<74.045:
        if t<62.589:
            # "If I can give you all the"
            lyric_stimulation_satisfaction(c,t,area,t-59.223)
        elif t<66.601:
            # "SATISFACTION"
            lyric_stimulation_satisfaction(c,t,area,t-59.223)
        elif t<70.084:
            lyric_happy_execution(c,t,area,pulse)
        elif t<74.045:
            lyric_trapped_simulation(c,t,area,pulse)

    # Original eggplant, tomato and cat; keep the revised god scene.
    elif t<85.078:
        legacy_organic(c,t,top,bt,pulse)
    elif t<88.587:
        lyric_god_existence(c,t,area,t-85.078)

    # Identity switching (88-103s)
    elif t<103.489:
        if t<92.015:
            # Gender switch F to M
            lyric_identity_rewrite(c,t,area)
        elif t<95.465:
            # AM to PM
            lyric_daynight_clock(c,t,area)
        elif t<99.349:
            # Role switch S to M
            lyric_gender_role_switch(c,t,area,t-95.465,'S','M')
        else:
            # Trance
            lyric_dizzy(c,t,area,t-99.349)

    # Vibration/completion (103-110s)
    elif t<110.9:
        lyric_vibration_sync(c,t,area,t-103.489)

    # Isolation (110-118s)
    elif t<118.333:
        lyric_isolation_disconnect(c,t,area,t-110.9)

    # Erase fragments (118-125s)
    elif t<125.708:
        lyric_erase_fragments(c,t,area,t-118.333)

    # Illegal arguments (125-147s)
    elif t<147.66:
        lyric_illegal_arguments(c,t,area,t-125.708)

    # EXECUTION section (147-177s)
    elif t<177.246:
        if t<158.9:
            # Repetitive EXECUTION
            lyric_execution_queue(c,t,area,t-147.66)
        elif t<162.632:
            lyric_multilingual_count(c,t,area)
        else:
            lyric_only_execution(c,t,area,pulse)

    # Love equation (177-192s)
    elif t<192.5:
        if t<188.483:
            # Love equation
            lyric_love_equation(c,t,area,t-177.246)
        else:
            # Trapped in love - prison with heart
            lyric_trapped_loop(c,t,area,min(t-188.483,4),pulse)

    # Outro (192+)
    else:
        lyric_outro_wait(c,t,area,t-192.5)

    # Apply escalating glitch effect
    if t<192.5 and not (74.045<=t<85.078 or 103.489<=t<110.9):apply_glitch(c,t,top,bt)

def phosphor(c,t,top,bt):
    """Luminance scan line effect"""
    if 74.045<=t<85.078:
        legacy_phosphor(c,t,top,bt)
        return
    intensity=glitch_intensity(t)
    # Less frequent scan in early sections, more in later
    if hash16(int(t*10))%100<intensity*50:
        row=top+int(t*9)%max(1,bt-top+1)
        for x in range(2,c.w-2):
            if row<len(c.cells) and x<len(c.cells[row]):
                ch,s=c.cells[row][x]
                if ch not in ('',' ') and s in (D,N,G):
                    c.cells[row][x]=(ch,N if s==G else B)
